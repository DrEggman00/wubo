#!/usr/bin/env python3
"""Gera assembly NASM (Intel, x86_64 SysV) a partir da IR gerada pelo compilador.

Uso: python emit_nasm.py <source.mc> [out.asm]

Gera arquivo `.asm` (NASM) que pode ser montado com `nasm -f elf64` e linkado com `gcc`.
"""
import sys
from ir import IRBuilder
import parser as myparser


def collect_names(instrs):
    names = []
    for ins in instrs:
        op = ins[0]
        if op == 'binop':
            _, dst, l, oper, r = ins
            if isinstance(l, str) and not l.startswith('t'):
                if l not in names:
                    names.append(l)
            if isinstance(r, str) and not r.startswith('t'):
                if r not in names:
                    names.append(r)
            if dst not in names:
                names.append(dst)
        elif op in ('assign', 'alloc', 'read'):
            _, dst, *rest = ins
            if dst not in names:
                names.append(dst)
        elif op == 'print':
            _, val = ins
            if isinstance(val, str) and not val.startswith('t'):
                if val not in names:
                    names.append(val)
        elif op == 'ret':
            _, val = ins
            if isinstance(val, str) and not val.startswith('t'):
                if val not in names:
                    names.append(val)
    return names


def collect_strings(instrs):
    strings = {}
    cnt = 0
    for ins in instrs:
        for item in ins[1:]:
            if isinstance(item, tuple) and item[0] == 'str':
                s = item[1]
                # strip surrounding quotes if present
                if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
                    s = s[1:-1]
                label = f".Lstr{cnt}"
                strings[s] = label
                cnt += 1
    return strings


def operand_to_imm(op):
    # returns (type, value) where type is 'imm', 'str', or 'name'
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


def gen_nasm(instrs, out_path):
    # collect names (vars & temps)
    names = []
    temps = []
    for ins in instrs:
        for item in ins[1:]:
            if isinstance(item, str):
                if item.startswith('t'):
                    if item not in temps:
                        temps.append(item)
                else:
                    if item not in names:
                        names.append(item)

    # all memory slots: names + temps
    mem_names = names + temps
    mem_map = {n: i for i, n in enumerate(mem_names)}

    strings = collect_strings(instrs)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('section .data\n')
        f.write('fmt_int: db "%ld", 10, 0\n')
        f.write('fmt_read: db "%ld", 0\n')
        for s, lbl in strings.items():
            # escape backslashes and quotes
            esc = s.replace('\\', '\\\\').replace('"', '\\"')
            f.write(f"{lbl}: db \"{esc}\",0\n")

        f.write('\nsection .bss\n')
        f.write(f'mem: resq {len(mem_names) if mem_names else 1}\n')

        f.write('\nsection .text\n')
        f.write('global main\n')
        f.write('extern printf, scanf, puts\n')
        f.write('\n')

        def load_operand(op, dst_reg):
            t, v = operand_to_imm(op)
            if t == 'imm':
                return [f'    mov {dst_reg}, {v}']
            if t == 'name':
                idx = mem_map[v]
                return [f'    mov {dst_reg}, [rel mem + {8*idx}]']
            if t == 'str':
                lbl = strings[v]
                return [f'    lea {dst_reg}, [rel {lbl}]']
            return [f'    mov {dst_reg}, {v}']

        for ins in instrs:
            op = ins[0]
            if op == 'func_begin':
                _, name = ins
                if name == 'MAIN':
                    f.write('main:\n')
                    f.write('    push rbp\n')
                    f.write('    mov rbp, rsp\n')
                else:
                    f.write(f'{name}:\n')
                    f.write('    push rbp\n')
                    f.write('    mov rbp, rsp\n')

            elif op == 'func_end':
                _, name = ins
                f.write('    mov rsp, rbp\n')
                f.write('    pop rbp\n')
                f.write('    ret\n')

            elif op == 'label':
                _, lbl = ins
                f.write(f'{lbl}:\n')

            elif op == 'goto':
                _, lbl = ins
                f.write(f'    jmp {lbl}\n')

            elif op == 'ifz':
                _, cond, lbl = ins
                # load cond into rax
                for line in load_operand(cond, 'rax'):
                    f.write(line + '\n')
                f.write('    cmp rax, 0\n')
                f.write(f'    je {lbl}\n')

            elif op == 'binop':
                _, dst, left, oper, right = ins
                # compute left -> rax
                for line in load_operand(left, 'rax'):
                    f.write(line + '\n')
                # compute right -> rbx
                for line in load_operand(right, 'rbx'):
                    f.write(line + '\n')

                if oper == 'OP_ADD':
                    f.write('    add rax, rbx\n')
                elif oper == 'OP_SUB':
                    f.write('    sub rax, rbx\n')
                elif oper == 'OP_MUL':
                    f.write('    imul rax, rbx\n')
                elif oper == 'OP_DIV':
                    f.write('    xor rdx, rdx\n')
                    f.write('    mov rsi, rbx\n')
                    f.write('    mov rbx, rsi\n')
                    f.write('    idiv rbx\n')
                elif oper == 'OP_EQ':
                    f.write('    cmp rax, rbx\n')
                    f.write('    sete al\n')
                    f.write('    movzx rax, al\n')
                elif oper == 'OP_NE':
                    f.write('    cmp rax, rbx\n')
                    f.write('    setne al\n')
                    f.write('    movzx rax, al\n')
                elif oper == 'OP_LT':
                    f.write('    cmp rax, rbx\n')
                    f.write('    setl al\n')
                    f.write('    movzx rax, al\n')
                elif oper == 'OP_GT':
                    f.write('    cmp rax, rbx\n')
                    f.write('    setg al\n')
                    f.write('    movzx rax, al\n')
                else:
                    f.write('    ; unsupported operator\n')

                # store result into dst (mem slot)
                idx = mem_map.get(dst, None)
                if idx is None:
                    # create if missing
                    idx = len(mem_map)
                    mem_map[dst] = idx
                f.write(f'    mov [rel mem + {8*idx}], rax\n')

            elif op == 'assign':
                _, dst, src = ins
                for line in load_operand(src, 'rax'):
                    f.write(line + '\n')
                idx = mem_map.get(dst, None)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[dst] = idx
                f.write(f'    mov [rel mem + {8*idx}], rax\n')

            elif op == 'alloc':
                # alloc does not emit runtime code; handled by mem size
                _, name = ins
                if name not in mem_map:
                    mem_map[name] = len(mem_map)

            elif op == 'read':
                _, name = ins
                idx = mem_map.get(name, None)
                if idx is None:
                    idx = len(mem_map)
                    mem_map[name] = idx
                f.write('    lea rdi, [rel fmt_read]\n')
                f.write(f'    lea rsi, [rel mem + {8*idx}]\n')
                f.write('    xor rax, rax\n')
                f.write('    call scanf\n')

            elif op == 'print':
                _, val = ins
                t, v = operand_to_imm(val)
                if t == 'str':
                    lbl = strings[v]
                    f.write(f'    lea rdi, [rel {lbl}]\n')
                    f.write('    call puts\n')
                else:
                    # numeric or name
                    for line in load_operand(val, 'rsi'):
                        # load into rsi for printf second arg
                        # if load_operand loads into rsi directly, keep it
                        f.write(line.replace('mov rax', 'mov rsi') + '\n')
                    f.write('    lea rdi, [rel fmt_int]\n')
                    f.write('    xor rax, rax\n')
                    f.write('    call printf\n')

            elif op == 'ret':
                _, val = ins
                for line in load_operand(val, 'rax'):
                    f.write(line + '\n')
                f.write('    mov rsp, rbp\n')
                f.write('    pop rbp\n')
                f.write('    ret\n')

            elif op == 'comment':
                _, text = ins
                f.write(f'    ; {text}\n')

            else:
                f.write(f'    ; UNKNOWN INSTR: {ins}\n')

    print(f'Generated NASM file: {out_path}')


def main():
    if len(sys.argv) < 2:
        print('Usage: python emit_nasm.py <source.mc> [out.asm]')
        return
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else 'out_nasm.asm'

    with open(src, 'r', encoding='utf-8') as f:
        data = f.read()

    ast_root = myparser.parse(data)
    if not ast_root:
        print('Parse error')
        return

    ir = IRBuilder().generate(ast_root)
    gen_nasm(ir, out)


if __name__ == '__main__':
    main()
