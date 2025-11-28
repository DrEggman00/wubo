# codegen.py
"""
Codegen simples: converte IR em assembly estilo "stack machine" / pseudo-x86.
Cada operação binária gera:
    LOAD <op>
    LOAD <op>
    <instr>
Temporários e variáveis são armazenados em uma tabela.
"""

from typing import List, Tuple, Any

Instr = Tuple[Any, ...]


class CodeGen:
    def __init__(self):
        self.asm = []
        self.varmap = {}   # mapeia variáveis -> endereço
        self.tempmap = {}  # mapeia temporários -> endereço
        self.mem_counter = 0  # contador de memória simulada

    def alloc(self, name):
        """Aloca um slot de memória para uma var ou temp."""
        if name not in self.varmap:
            self.varmap[name] = self.mem_counter
            self.mem_counter += 1

    def alloc_temp(self, name):
        if name not in self.tempmap:
            self.tempmap[name] = self.mem_counter
            self.mem_counter += 1

    def emit(self, line):
        self.asm.append(line)

    def operand(self, op):
        """Retorna instrução para carregar operandos."""
        if isinstance(op, tuple) and op[0] == "imm":
            return f"push {op[1]}"
        if isinstance(op, tuple) and op[0] == "str":
            return f"push \"{op[1]}\""
"""
CodeGen atualizado para gerar assembly NASM (Intel x86_64 SysV).

Gera .data com literais de string, .bss com vetor `mem`, e .text com funções/labels.
Usa `printf`/`scanf`/`puts` para I/O.
"""

from typing import List, Tuple, Any

Instr = Tuple[Any, ...]


class CodeGen:
    def __init__(self):
        pass

    def generate(self, ir: List[Instr]) -> str:
        # gather mem names (variables and temps) and strings
        mem_names = []
        temps = []
        strings = {}
        str_count = 0

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
                        strings[s] = f'.Lstr{str_count}'
                        str_count += 1

        all_mem = mem_names + temps
        mem_map = {n: i for i, n in enumerate(all_mem)}

        lines: List[str] = []
        # data
        lines.append('section .data')
        lines.append('fmt_int: db "%ld", 10, 0')
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
            if t == 'name':
                idx = mem_map.get(v, 0)
                return [f'    mov {reg}, [rel mem + {8*idx}]']
            if t == 'str':
                lbl = strings[v]
                return [f'    lea {reg}, [rel {lbl}]']
            return [f'    mov {reg}, {v}']

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
