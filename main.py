#!/usr/bin/env python3
# main.py

import sys
import io
from contextlib import redirect_stdout

import parser as myparser
from ast import pretty_print
from ir import IRBuilder, ir_to_text
from codegen import CodeGen


def compile_file(filename):
    print(f"[+] Compilando: {filename}")

    # 1. Ler código fonte
    with open(filename, "r", encoding="utf-8") as f:
        source = f.read()

    # 2. PARSER -> AST
    print("[+] Parsing...")
    ast_root = myparser.parse(source)
    if ast_root is None:
        print("Erro: não foi possível gerar AST (sintaxe).")
        return

    # 3. Exibir / salvar AST (capturando a saída do pretty_print)
    print("[+] Gerando AST...")
    buf = io.StringIO()
    with redirect_stdout(buf):
        pretty_print(ast_root)
    ast_text = buf.getvalue()
    with open("out.ast.txt", "w", encoding="utf-8") as f:
        f.write(ast_text)
    print("[✓] AST salvo em out.ast.txt")

    # 4. AST -> IR
    print("[+] Gerando IR...")
    ir_builder = IRBuilder()
    ir = ir_builder.generate(ast_root)
    ir_text = ir_to_text(ir)
    with open("out.ir.txt", "w", encoding="utf-8") as f:
        f.write(ir_text)
    print("[✓] IR salvo em out.ir.txt")

    # 5. IR -> Assembly
    print("[+] Gerando Assembly...")
    codegen = CodeGen()
    asm = codegen.generate(ir)
    with open("out.asm.txt", "w", encoding="utf-8") as f:
        f.write(asm)
    print("[✓] Assembly salvo em out.asm.txt")

    print("\n[✓] Compilação completa!\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <arquivo-fonte>")
        sys.exit(1)
    compile_file(sys.argv[1])


if __name__ == "__main__":
    main()
