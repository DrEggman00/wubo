# ir.py
from typing import List, Tuple, Any
from ast import (
    Program, Function, Block, Declaration, VarDecl, Assignment, Input, Output,
    While, Return, Comment, BinaryOp, Identifier, Number, StringLit
)

Instr = Tuple[Any, ...]  # instrução IR é uma tupla heterogênea

class IRBuilder:
    def __init__(self):
        self.instrs: List[Instr] = []
        self.temp_count = 0
        self.label_count = 0
        self.current_function = None

    # ---- utilitários ----
    def new_temp(self) -> str:
        t = f"t{self.temp_count}"
        self.temp_count += 1
        return t

    def new_label(self) -> str:
        L = f"L{self.label_count}"
        self.label_count += 1
        return L

    def emit(self, *args):
        self.instrs.append(tuple(args))

    # ---- entrada principal ----
    def generate(self, node):
        self.instrs = []
        self.temp_count = 0
        self.label_count = 0
        self.visit(node)
        return self.instrs

    # ---- visitor genérico ----
    def visit(self, node):
        if node is None:
            return None
        method = 'visit_' + node.__class__.__name__
        if hasattr(self, method):
            return getattr(self, method)(node)
        raise NotImplementedError(f"No visit method for {node.__class__.__name__}")

    # ---- nós do programa/funcões ----
    def visit_Program(self, node: Program):
        # node.functions: list[Function]
        for func in node.functions:
            self.visit(func)

    def visit_Function(self, node: Function):
        fname = node.name
        self.current_function = fname
        self.emit('func_begin', fname)
        # prologue could go here (frame setup)
        self.visit(node.block)
        # se função não tiver return explícito, garante return None
        self.emit('func_end', fname)
        self.current_function = None

    def visit_Block(self, node: Block):
        for cmd in node.commands:
            self.visit(cmd)

    # ---- comandos ----
    def visit_Declaration(self, node: Declaration):
        # node.decls : list of VarDecl
        for decl in node.decls:
            # só gera atribuição se houver init
            if decl.init is not None:
                rhs = self.visit(decl.init)
                # init pode devolver temp ou immediate; atribuímos ao nome da var
                self.emit('assign', decl.name, rhs)
            else:
                # declaração sem inicialização: opcional gerar 'alloc' ou nada
                self.emit('alloc', decl.name)  # informativo

    def visit_VarDecl(self, node: VarDecl):
        # raramente chamado isoladamente porque handled in Declaration
        if node.init:
            val = self.visit(node.init)
            self.emit('assign', node.name, val)
        else:
            self.emit('alloc', node.name)

    def visit_Assignment(self, node: Assignment):
        rhs = self.visit(node.expr)
        self.emit('assign', node.name, rhs)

    def visit_Input(self, node: Input):
        # INPUT ID ;
        self.emit('read', node.name)

    def visit_Output(self, node: Output):
        val = self.visit(node.expr)
        self.emit('print', val)

    def visit_While(self, node: While):
        start = self.new_label()
        end = self.new_label()
        self.emit('label', start)
        cond_temp = self.visit(node.cond)
        # if cond == 0 goto end  -> here 'ifz'
        self.emit('ifz', cond_temp, end)
        self.visit(node.block)
        self.emit('goto', start)
        self.emit('label', end)

    def visit_Return(self, node: Return):
        val = self.visit(node.expr)
        self.emit('ret', val)

    def visit_Comment(self, node: Comment):
        # não gera IR, mas podemos guardar como comentário instr
        self.emit('comment', node.text)

    # ---- expressões ----
    def visit_BinaryOp(self, node: BinaryOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        # se left/right forem nomes literais (variáveis) ou temporários, tudo ok
        # garante que left/right sejam operandos (se Number -> immediate)
        temp = self.new_temp()
        self.emit('binop', temp, left, node.op, right)
        return temp

    def visit_Identifier(self, node: Identifier):
        return node.name

    def visit_Number(self, node: Number):
        # mantemos o lexema string, mas marcamos como immediate
        return ('imm', node.value)

    def visit_StringLit(self, node: StringLit):
        return ('str', node.value)

# ---- util para exibir IR de forma legível ----
def ir_to_text(instrs: List[Instr]) -> str:
    lines = []
    for ins in instrs:
        op = ins[0]
        if op == 'binop':
            _, dst, l, oper, r = ins
            lines.append(f"{dst} = {format_operand(l)} {oper} {format_operand(r)}")
        elif op == 'assign':
            _, dst, src = ins
            lines.append(f"{dst} = {format_operand(src)}")
        elif op == 'alloc':
            _, var = ins
            lines.append(f"# alloc {var}")
        elif op == 'label':
            _, lab = ins
            lines.append(f"{lab}:")
        elif op == 'goto':
            _, lab = ins
            lines.append(f"goto {lab}")
        elif op == 'ifz':
            _, cond, lab = ins
            lines.append(f"if {format_operand(cond)} == 0 goto {lab}")
        elif op == 'read':
            _, var = ins
            lines.append(f"read {var}")
        elif op == 'print':
            _, val = ins
            lines.append(f"print {format_operand(val)}")
        elif op == 'ret':
            _, val = ins
            lines.append(f"return {format_operand(val)}")
        elif op == 'func_begin':
            _, name = ins
            lines.append(f"func {name} begin")
        elif op == 'func_end':
            _, name = ins
            lines.append(f"func {name} end")
        elif op == 'comment':
            _, text = ins
            lines.append(f"# {text}")
        else:
            lines.append(str(ins))
    return "\n".join(lines)

def format_operand(op):
    if isinstance(op, tuple) and len(op) >= 1:
        tag = op[0]
        if tag == 'imm':
            return op[1]
        if tag == 'str':
            return op[1]
    return str(op)


# ---- exemplo rápido de uso (se executado diretamente) ----
if __name__ == "__main__":
    # exemplo construtor simples (sem usar parser) para teste rápido:
    prog = Program([
        Function("MAIN",
            Block([
                Declaration("INT", [VarDecl("X", Number("5"))]),
                Assignment("X", BinaryOp(Identifier("X"), "OP_ADD", Number("1"))),
                Output(Identifier("X")),
                While(BinaryOp(Identifier("X"), "OP_LT", Number("10")),
                      Block([
                          Assignment("X", BinaryOp(Identifier("X"), "OP_ADD", Number("1")))
                      ])
                ),
                Return(Identifier("X"))
            ])
        )
    ])

    builder = IRBuilder()
    ir = builder.generate(prog)
    print(ir_to_text(ir))
