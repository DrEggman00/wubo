# ast.py
from typing import List, Optional, Any


class Node:
    """Base class para todos os nós."""
    def accept(self, visitor):
        method = 'visit_' + self.__class__.__name__
        return getattr(visitor, method, visitor.generic_visit)(self)


# Programa e funções
class Program(Node):
    def __init__(self, functions: List['Function']):
        self.functions = functions

class Function(Node):
    def __init__(self, name: str, block: 'Block'):
        self.name = name
        self.block = block


# Blocos e comandos
class Block(Node):
    def __init__(self, commands: List['Command']):
        self.commands = commands

class Command(Node):
    pass

class Declaration(Command):
    def __init__(self, var_type: str, decls: List['VarDecl']):
        self.var_type = var_type
        self.decls = decls  # list of VarDecl

class VarDecl(Node):
    def __init__(self, name: str, init: Optional['Expr']):
        self.name = name
        self.init = init

class Assignment(Command):
    def __init__(self, name: str, expr: 'Expr'):
        self.name = name
        self.expr = expr

class Input(Command):
    def __init__(self, name: str):
        self.name = name

class Output(Command):
    def __init__(self, expr: 'Expr'):
        self.expr = expr

class While(Command):
    def __init__(self, cond: 'Expr', block: Block):
        self.cond = cond
        self.block = block

class Return(Command):
    def __init__(self, expr: 'Expr'):
        self.expr = expr

class Comment(Command):
    def __init__(self, text: str):
        self.text = text


# Expressões
class Expr(Node):
    pass

class BinaryOp(Expr):
    def __init__(self, left: Expr, op: str, right: Expr):
        self.left = left
        self.op = op
        self.right = right

class Identifier(Expr):
    def __init__(self, name: str):
        self.name = name

class Number(Expr):
    def __init__(self, value: str):
        # mantemos como string para preservar lexema; conversão posterior é fácil
        self.value = value

class StringLit(Expr):
    def __init__(self, value: str):
        self.value = value


# ----------------------------
# Pretty-print helper
# ----------------------------
def pretty_print(node: Node, indent: int = 0):
    pad = '  ' * indent
    if isinstance(node, Program):
        print(f"{pad}Program")
        for f in node.functions:
            pretty_print(f, indent+1)
    elif isinstance(node, Function):
        print(f"{pad}Function: {node.name}")
        pretty_print(node.block, indent+1)
    elif isinstance(node, Block):
        print(f"{pad}Block")
        for c in node.commands:
            pretty_print(c, indent+1)
    elif isinstance(node, Declaration):
        print(f"{pad}Declaration: {node.var_type}")
        for d in node.decls:
            pretty_print(d, indent+1)
    elif isinstance(node, VarDecl):
        print(f"{pad}VarDecl: {node.name}")
        if node.init:
            pretty_print(node.init, indent+1)
    elif isinstance(node, Assignment):
        print(f"{pad}Assignment: {node.name} =")
        pretty_print(node.expr, indent+1)
    elif isinstance(node, Input):
        print(f"{pad}Input: {node.name}")
    elif isinstance(node, Output):
        print(f"{pad}Output:")
        pretty_print(node.expr, indent+1)
    elif isinstance(node, While):
        print(f"{pad}While")
        pretty_print(node.cond, indent+1)
        pretty_print(node.block, indent+1)
    elif isinstance(node, Return):
        print(f"{pad}Return")
        pretty_print(node.expr, indent+1)
    elif isinstance(node, Comment):
        print(f"{pad}Comment: {node.text}")
    elif isinstance(node, BinaryOp):
        print(f"{pad}BinaryOp: {node.op}")
        pretty_print(node.left, indent+1)
        pretty_print(node.right, indent+1)
    elif isinstance(node, Identifier):
        print(f"{pad}Identifier: {node.name}")
    elif isinstance(node, Number):
        print(f"{pad}Number: {node.value}")
    elif isinstance(node, StringLit):
        print(f"{pad}String: {node.value}")
    else:
        print(f"{pad}<Unknown node {type(node).__name__}>")
