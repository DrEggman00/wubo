#!/usr/bin/env python3
# main.py

import sys
from lexer import lexer
from parser import parser
from ast import ast
from ir import IRBuilder, ir_to_text
from codegen import codegen


def compile_file(filename):
    print(f"[+] Compilando: {filename}")

    # -----------------------------------------------------------
    # 1. Ler código fonte
    # -----------------------------------------------------------
    with open(filename, "r", encoding="utf-8") as f:
        source = f.read()

    # -----------------------------------------------------------
    # 2. LEXER
    # -----------------------------------------------------------
    print("[+] Lexing...")
    lexer = Lexer(source)
    tokens = list(lexer.tokenize())

    # opção: imprimir tokens
    # for t in tokens:
    #     print(t)

    # -----------------------------------------------------------
    # 3. PARSER -> AST
    # -----------------------------------------------------------
    print("[+] Parsing...")
    parser = Parser(tokens)
    ast = parser.parse_program()

    # -----------------------------------------------------------
    # 4. Exibir AST
    # -----------------------------------------------------------
    print("[+] Gerando AST...")
    printer = ASTPrinter()
    ast_text = printer.print(ast)

    with open("out.ast.txt", "w", encoding="utf-8") as f:
        f.write(ast_text)

    print("[✓] AST salvo em out.ast.txt")

    # -----------------------------------------------------------
    # 5. AST -> IR
    # -----------------------------------------------------------
    print("[+] Gerando IR...")
    ir_builder = IRBuilder()
    ir = ir_builder.generate(ast)

    ir_text = ir_to_text(ir)

    with open("out.ir.txt", "w", encoding="utf-8") as f:
        f.write(ir_text)

    print("[✓] IR salvo em out.ir.txt")

    # -----------------------------------------------------------
    # 6. IR -> Assembly
    # -----------------------------------------------------------
    print("[+] Gerando Assembly...")
    codegen = CodeGen()
    asm = codegen.generate(ir)

    with open("out.asm.txt", "w", encoding="utf-8") as f:
        f.write(asm)

    print("[✓] Assembly salvo em out.asm.txt")

    print("\n[✓] Compilação completa!\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 main.py <arquivo-fonte>")
        sys.exit(1)

    compile_file(sys.argv[1])


if __name__ == "__main__":
    main()
