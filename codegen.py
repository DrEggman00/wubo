from typing import List, Tuple, Any, Dict

Instr = Tuple[Any, ...]


class CodeGen:
    """Gerador de assembly NASM (Intel x86_64 SysV) a partir da IR.

    - Emite `.data` com literais e formatos (`fmt_int`, `fmt_str`, `fmt_read`, `fmt_concat`).
    - Emite `.bss` com vetor `mem` (slots para variáveis e temporários) e buffers para concatenação.
    - Emite `.text` com `global main` e chamadas a `printf/scanf/puts/sprintf`.

    Notas sobre tipagem: a IR não carrega tipos explícitos. Fazemos uma varredura
    heurística para marcar nomes/temporários como `str` quando recebem literais
    de string ou quando uma operação `+` envolve uma string. Isso permite usar
    `puts`/`printf` adequadamente e gerar concatenação simples via `sprintf`.
    """

    def __init__(self):
        pass

    def generate(self, ir: List[Instr]) -> str:
        # --- first pass: discover mem names, temps, and simple types ---
        mem_names: List[str] = []
        temps: List[str] = []
        strings: Dict[str, str] = {}
        str_count = 0

        # simple type inference: map name -> 'str'|'int'
        vtypes: Dict[str, str] = {}

        for ins in ir:
            op = ins[0]
            # collect names and detect string literals occurrences
            for item in ins[1:]:
                if isinstance(item, str):
                    if item.startswith('t'):
                        if item not in temps:
                            temps.append(item)
                    else:
                        if item not in mem_names:
                            mem_names.append(item)
                elif isinstance(item, tuple) and item[0] == 'str':
                    s = item[1]
                    # strip quotes if present
                    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
                        s = s[1:-1]
                    if s not in strings:
                        strings[s] = f'Lstr{str_count}'
                        str_count += 1

            # type inference heuristics
            if op == 'assign':
                _, dst, src = ins
                if isinstance(src, tuple) and src[0] == 'str':
                    vtypes[dst] = 'str'
            elif op == 'binop':
                _, dst, left, oper, right = ins
                left_is_str = (isinstance(left, tuple) and left[0] == 'str') or (isinstance(left, str) and vtypes.get(left) == 'str')
                right_is_str = (isinstance(right, tuple) and right[0] == 'str') or (isinstance(right, str) and vtypes.get(right) == 'str')
                if oper in ('OP_ADD', '+') and (left_is_str or right_is_str):
                    vtypes[dst] = 'str'
                else:
                    vtypes[dst] = 'int'
            elif op == 'read':
                _, name = ins
                vtypes[name] = 'int'

        all_mem = mem_names + temps
        mem_map = {n: i for i, n in enumerate(all_mem)}

        # prepare buffers for temps that are string-typed
        buf_map: Dict[str, str] = {}
        buf_count = 0
        for t in temps:
            if vtypes.get(t) == 'str':
                buf_map[t] = f'buf{buf_count}'
                buf_count += 1

        lines: List[str] = []

        # --- data section ---
        lines.append('section .data')
        lines.append('fmt_int: db "%ld", 10, 0')
        lines.append('fmt_str: db "%s", 10, 0')
        lines.append('fmt_read: db "%ld", 0')
        lines.append('fmt_concat: db "%s%s", 0')
        for s, lbl in strings.items():
            esc = s.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{lbl}: db "{esc}",0')

        # --- bss section ---
        lines.append('')
        lines.append('section .bss')
        lines.append(f'mem: resq {len(all_mem) if all_mem else 1}')
        for t, lbl in buf_map.items():
            lines.append(f'{lbl}: resb 256')

        # --- text section ---
        lines.append('')
        lines.append('section .text')
        lines.append('global main')
        lines.append('extern printf, scanf, puts, sprintf')
        lines.append('')

        def operand_to_imm(op):
            if isinstance(op, tuple):
                if op[0] == 'imm':
                    return ('imm', int(op[1]))
                if op[0] == 'str':
                    s = op[1]
                    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
                        s = s[1:-1]
                    return ('str', s)
            if isinstance(op, str):
                return ('name', op)
            return ('imm', int(op))

        def load_operand(op, reg):
            """Return list of assembly lines that load `op` into register `reg`.
            For string-typed names, load pointer value; for immediates and ints load value.
            For string immediate, lea the label into reg.
            """
            t, v = operand_to_imm(op)
            if t == 'imm':
                return [f'    mov {reg}, {v}']
            if t == 'name':
                idx = mem_map.get(v, 0)
                return [f'    mov {reg}, [rel mem + {8*idx}]']
            if t == 'str':
                lbl = strings[v]
                return [f'    lea {reg}, [rel {lbl}]']
            return [f'    mov {reg}, {v}']

        # --- generate code by walking IR ---
        for ins in ir:
            op = ins[0]

            if op == 'func_begin':
                _, name = ins
                if name == 'MAIN':
                    lines.append('main:')
                    lines.append('    push rbp')
                    lines.append('    mov rbp, rsp')
                else:
                    lines.append(f'{name}:')
                    lines.append('    push rbp')
                    lines.append('    mov rbp, rsp')

            elif op == 'func_end':
                lines.append('    mov rsp, rbp')
                lines.append('    pop rbp')
                lines.append('    ret')

            elif op == 'label':
                _, lbl = ins
                lines.append(f'{lbl}:')

            elif op == 'goto':
                _, lbl = ins
                lines.append(f'    jmp {lbl}')

            elif op == 'ifz':
                _, cond, lbl = ins
                for l in load_operand(cond, 'rax'):
                    lines.append(l)
                lines.append('    cmp rax, 0')
                lines.append(f'    je {lbl}')

            elif op == 'binop':
                _, dst, left, oper, right = ins
                left_t, _ = operand_to_imm(left)
                right_t, _ = operand_to_imm(right)
                left_is_str = (left_t == 'str') or (isinstance(left, str) and vtypes.get(left) == 'str')
                right_is_str = (right_t == 'str') or (isinstance(right, str) and vtypes.get(right) == 'str')

                if oper in ('OP_ADD', '+') and (left_is_str or right_is_str):
                    idx = mem_map.get(dst)
                    if idx is None:
                        idx = len(mem_map)
                        mem_map[dst] = idx
                    buf_lbl = buf_map.get(dst)
                    if not buf_lbl:
                        buf_lbl = f'buf{len(buf_map)}'
                        buf_map[dst] = buf_lbl
                        lines.insert(3 + len(strings), f'{buf_lbl}: resb 256')

                    for l in load_operand(left, 'rdx'):
                        lines.append(l)
                    for l in load_operand(right, 'rcx'):
                        lines.append(l)
                    lines.append(f'    lea rdi, [rel {buf_lbl}]')
                    lines.append('    lea rsi, [rel fmt_concat]')
                    lines.append('    call sprintf')
                    lines.append('    lea rax, [rel %s]' % buf_lbl)
                    lines.append(f'    mov [rel mem + {8*idx}], rax')
                    vtypes[dst] = 'str'
                else:
                    for l in load_operand(left, 'rax'):
                        lines.append(l)
                    for l in load_operand(right, 'rbx'):
                        lines.append(l)

                    if oper in ('OP_ADD', '+'):
                        lines.append('    add rax, rbx')
                    elif oper in ('OP_SUB', '-'):
                        lines.append('    sub rax, rbx')
                    elif oper in ('OP_MUL', '*'):
                        lines.append('    imul rax, rbx')
                    elif oper in ('OP_DIV', '/'):
                        lines.append('    xor rdx, rdx')
                        lines.append('    idiv rbx')
                    elif oper in ('OP_EQ', '=='):
                        lines.append('    cmp rax, rbx')
                        lines.append('    sete al')
                        lines.append('    movzx rax, al')
                    elif oper in ('OP_NE', '!='):
                        lines.append('    cmp rax, rbx')
                        lines.append('    setne al')
                        lines.append('    movzx rax, al')
                    elif oper in ('OP_LT', '<'):
                        lines.append('    cmp rax, rbx')
                        lines.append('    setl al')
                        lines.append('    movzx rax, al')
                    elif oper in ('OP_GT', '>'):
                        lines.append('    cmp rax, rbx')
                        lines.append('    setg al')
                        lines.append('    movzx rax, al')
                    else:
                        lines.append('    ; unsupported operator')

                    idx = mem_map.get(dst)
                    if idx is None:
                        idx = len(mem_map)
                        mem_map[dst] = idx
                    lines.append(f'    mov [rel mem + {8*idx}], rax')
                    vtypes[dst] = 'int'

            elif op == 'assign':
                _, dst, src = ins
                idx = mem_map.get(dst)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[dst] = idx
                t, v = operand_to_imm(src)
                if t == 'str':
                    lbl = strings[v]
                    lines.append(f'    lea rax, [rel {lbl}]')
                    lines.append(f'    mov [rel mem + {8*idx}], rax')
                    vtypes[dst] = 'str'
                else:
                    for l in load_operand(src, 'rax'):
                        lines.append(l)
                    lines.append(f'    mov [rel mem + {8*idx}], rax')
                    vtypes[dst] = 'int'

            elif op == 'alloc':
                _, name = ins
                if name not in mem_map:
                    mem_map[name] = len(mem_map)

            elif op == 'read':
                _, name = ins
                idx = mem_map.get(name)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[name] = idx
                lines.append('    lea rdi, [rel fmt_read]')
                lines.append(f'    lea rsi, [rel mem + {8*idx}]')
                lines.append('    xor rax, rax')
                lines.append('    call scanf')
                vtypes[name] = 'int'

            elif op == 'print':
                _, val = ins
                t, v = operand_to_imm(val)
                if t == 'str':
                    lbl = strings[v]
                    lines.append(f'    lea rdi, [rel {lbl}]')
                    lines.append('    call puts')
                elif t == 'name':
                    if vtypes.get(v) == 'str':
                        idx = mem_map.get(v, 0)
                        lines.append(f'    mov rdi, [rel mem + {8*idx}]')
                        lines.append('    call puts')
                    else:
                        idx = mem_map.get(v, 0)
                        lines.append(f'    mov rsi, [rel mem + {8*idx}]')
                        lines.append('    lea rdi, [rel fmt_int]')
                        lines.append('    xor rax, rax')
                        lines.append('    call printf')
                else:
                    for l in load_operand(val, 'rsi'):
                        lines.append(l.replace('mov rax', 'mov rsi'))
                    lines.append('    lea rdi, [rel fmt_int]')
                    lines.append('    xor rax, rax')
                    lines.append('    call printf')

            elif op == 'ret':
                _, val = ins
                for l in load_operand(val, 'rax'):
                    lines.append(l)
                lines.append('    mov rsp, rbp')
                lines.append('    pop rbp')
                lines.append('    ret')

            elif op == 'comment':
                _, text = ins
                lines.append(f'    ; {text}')

            else:
                lines.append(f'    ; UNKNOWN INSTR: {ins}')

        return "\n".join(lines)
        for ins in ir:
            for item in ins[1:]:
                if isinstance(item, str):
                    if item.startswith('t'):
                        if item not in temps:
                            temps.append(item)
                    else:
                        if item not in mem_names:
                            mem_names.append(item)
                elif isinstance(item, tuple) and item[0] == 'str':
                    s = item[1]
                    # strip surrounding quotes
                    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
                        s = s[1:-1]
                    if s not in strings:
                        strings[s] = f'Lstr{str_count}'
                        str_count += 1

        all_mem = mem_names + temps
        mem_map = {n: i for i, n in enumerate(all_mem)}

        lines: List[str] = []
        # data
        lines.append('section .data')
        lines.append('fmt_int: db "%ld", 10, 0')
        lines.append('fmt_str: db "%s", 10, 0')
        lines.append('fmt_read: db "%ld", 0')
        for s, lbl in strings.items():
            esc = s.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{lbl}: db "{esc}",0')

        # bss
        lines.append('')
        lines.append('section .bss')
        lines.append(f'mem: resq {len(all_mem) if all_mem else 1}')

        # text
        lines.append('')
        lines.append('section .text')
        lines.append('global main')
        lines.append('extern printf, scanf, puts')
        lines.append('')

        def operand_to_imm(op):
            if isinstance(op, tuple):
                if op[0] == 'imm':
                    return ('imm', int(op[1]))
                if op[0] == 'str':
                    s = op[1]
                    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
                        s = s[1:-1]
                    return ('str', s)
            if isinstance(op, str):
                return ('name', op)
            return ('imm', int(op))

        def load_operand(op, reg):
            t, v = operand_to_imm(op)
            if t == 'imm':
                return [f'    mov {reg}, {v}']
                if t == 'str':
                    lbl = strings[v]
                    lines.append(f'    lea rdi, [rel {lbl}]')
                    lines.append('    call puts')
                elif t == 'name':
                    # assume variable stores pointer to string; use puts
                    idx = mem_map.get(v, 0)
                    lines.append(f'    mov rdi, [rel mem + {8*idx}]')
                    lines.append('    call puts')
                else:
                    # immediate numeric
                    for l in load_operand(val, 'rsi'):
                        lines.append(l.replace('mov rax', 'mov rsi'))
                    lines.append('    lea rdi, [rel fmt_int]')
                    lines.append('    xor rax, rax')
                    lines.append('    call printf')
                    lines.append('main:')
                    lines.append('    push rbp')
                    lines.append('    mov rbp, rsp')
                else:
                    lines.append(f'{name}:')
                    lines.append('    push rbp')
                    lines.append('    mov rbp, rsp')

            elif op == 'func_end':
                lines.append('    mov rsp, rbp')
                lines.append('    pop rbp')
                lines.append('    ret')

            elif op == 'label':
                _, lbl = ins
                lines.append(f'{lbl}:')

            elif op == 'goto':
                _, lbl = ins
                lines.append(f'    jmp {lbl}')

            elif op == 'ifz':
                _, cond, lbl = ins
                for l in load_operand(cond, 'rax'):
                    lines.append(l)
                lines.append('    cmp rax, 0')
                lines.append(f'    je {lbl}')

            elif op == 'binop':
                _, dst, left, oper, right = ins
                for l in load_operand(left, 'rax'):
                    lines.append(l)
                for l in load_operand(right, 'rbx'):
                    lines.append(l)

                if oper in ('OP_ADD', '+'):
                    lines.append('    add rax, rbx')
                elif oper in ('OP_SUB', '-'):
                    lines.append('    sub rax, rbx')
                elif oper in ('OP_MUL', '*'):
                    lines.append('    imul rax, rbx')
                elif oper in ('OP_DIV', '/'):
                    lines.append('    xor rdx, rdx')
                    lines.append('    idiv rbx')
                elif oper in ('OP_EQ', '=='):
                    lines.append('    cmp rax, rbx')
                    lines.append('    sete al')
                    lines.append('    movzx rax, al')
                elif oper in ('OP_NE', '!='):
                    lines.append('    cmp rax, rbx')
                    lines.append('    setne al')
                    lines.append('    movzx rax, al')
                elif oper in ('OP_LT', '<'):
                    lines.append('    cmp rax, rbx')
                    lines.append('    setl al')
                    lines.append('    movzx rax, al')
                elif oper in ('OP_GT', '>'):
                    lines.append('    cmp rax, rbx')
                    lines.append('    setg al')
                    lines.append('    movzx rax, al')
                else:
                    lines.append('    ; unsupported operator')

                idx = mem_map.get(dst)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[dst] = idx
                lines.append(f'    mov [rel mem + {8*idx}], rax')

            elif op == 'assign':
                _, dst, src = ins
                for l in load_operand(src, 'rax'):
                    lines.append(l)
                idx = mem_map.get(dst)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[dst] = idx
                lines.append(f'    mov [rel mem + {8*idx}], rax')

            elif op == 'alloc':
                _, name = ins
                if name not in mem_map:
                    mem_map[name] = len(mem_map)

            elif op == 'read':
                _, name = ins
                idx = mem_map.get(name)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[name] = idx
                lines.append('    lea rdi, [rel fmt_read]')
                lines.append(f'    lea rsi, [rel mem + {8*idx}]')
                lines.append('    xor rax, rax')
                lines.append('    call scanf')

            elif op == 'print':
                _, val = ins
                t, v = operand_to_imm(val)
                if t == 'str':
                    lbl = strings[v]
                    lines.append(f'    lea rdi, [rel {lbl}]')
                    lines.append('    call puts')
                else:
                    for l in load_operand(val, 'rsi'):
                        lines.append(l.replace('mov rax', 'mov rsi'))
                    lines.append('    lea rdi, [rel fmt_int]')
                    lines.append('    xor rax, rax')
                    lines.append('    call printf')

            elif op == 'ret':
                _, val = ins
                for l in load_operand(val, 'rax'):
                    lines.append(l)
                lines.append('    mov rsp, rbp')
                lines.append('    pop rbp')
                lines.append('    ret')

            elif op == 'comment':
                _, text = ins
                lines.append(f'    ; {text}')

            else:
                lines.append(f'    ; UNKNOWN INSTR: {ins}')

        return "\n".join(lines)
