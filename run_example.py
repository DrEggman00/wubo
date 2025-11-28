#!/usr/bin/env python3
"""Script auxiliar para executar o exemplo `hello.mc` usando as APIs existentes.
Imprime AST, IR e pseudo-assembly no terminal.
"""
from ast import pretty_print
import parser as myparser
from ir import IRBuilder, ir_to_text
from codegen import CodeGen


def main():
    with open("hello.mc", "r", encoding="utf-8") as f:
        src = f.read()

    ast_root = myparser.parse(src)
    if not ast_root:
        print("Falha ao gerar AST (provável erro de sintaxe).")
        return

    print("--- AST ---")
    pretty_print(ast_root)

    print("\n--- IR ---")
    ir = IRBuilder().generate(ast_root)
    print(ir_to_text(ir))

    print("\n--- Assembly (pseudo) ---")
    asm = CodeGen().generate(ir)
    print(asm)


if __name__ == "__main__":
    main()
