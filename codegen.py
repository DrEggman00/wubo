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

        # variável ou temp
        if op in self.varmap:
            return f"push [mem+{self.varmap[op]}]"
        if op in self.tempmap:
            return f"push [mem+{self.tempmap[op]}]"

        # se não existe ainda, aloca como var
        self.alloc(op)
        return f"push [mem+{self.varmap[op]}]"

    def generate(self, ir: List[Instr]):
        """Converte lista de IR em assembly."""
        self.asm = []

        for ins in ir:
            op = ins[0]

            # -----------------------------------------------------
            # FUNÇÃO
            # -----------------------------------------------------
            if op == "func_begin":
                _, name = ins
                self.emit(f"{name}:")
                self.emit("    ; prologue")
                self.emit("    push rbp")
                self.emit("    mov rbp, rsp")

            elif op == "func_end":
                _, name = ins
                self.emit("    ; epilogue")
                self.emit("    mov rsp, rbp")
                self.emit("    pop rbp")
                self.emit("    ret")

            # -----------------------------------------------------
            # LABEL
            # -----------------------------------------------------
            elif op == "label":
                _, lbl = ins
                self.emit(f"{lbl}:")

            # -----------------------------------------------------
            # GOTO
            # -----------------------------------------------------
            elif op == "goto":
                _, lbl = ins
                self.emit(f"    jmp {lbl}")

            # -----------------------------------------------------
            # IFZ (if zero)
            # -----------------------------------------------------
            elif op == "ifz":
                _, cond, lbl = ins
                self.emit("    ; if zero")
                self.emit(f"    {self.operand(cond)}")
                self.emit("    pop rax")
                self.emit(f"    cmp rax, 0")
                self.emit(f"    je {lbl}")

            # -----------------------------------------------------
            # BINOP
            # -----------------------------------------------------
            elif op == "binop":
                _, dst, left, oper, right = ins

                # aloca temp
                self.alloc_temp(dst)

                # empilha operandos
                self.emit(f"    ; {dst} = {left} {oper} {right}")
                self.emit(f"    {self.operand(left)}")
                self.emit(f"    {self.operand(right)}")
                self.emit("    pop rbx")
                self.emit("    pop rax")

                # escolhe instrução
                if oper == "OP_ADD":
                    self.emit("    add rax, rbx")
                elif oper == "OP_SUB":
                    self.emit("    sub rax, rbx")
                elif oper == "OP_MUL":
                    self.emit("    imul rax, rbx")
                elif oper == "OP_DIV":
                    self.emit("    xor rdx, rdx")
                    self.emit("    idiv rbx")
                elif oper == "OP_EQ":
                    self.emit("    cmp rax, rbx")
                    self.emit("    sete al")
                    self.emit("    movzx rax, al")
                elif oper == "OP_NE":
                    self.emit("    cmp rax, rbx")
                    self.emit("    setne al")
                    self.emit("    movzx rax, al")
                elif oper == "OP_LT":
                    self.emit("    cmp rax, rbx")
                    self.emit("    setl al")
                    self.emit("    movzx rax, al")
                elif oper == "OP_GT":
                    self.emit("    cmp rax, rbx")
                    self.emit("    setg al")
                    self.emit("    movzx rax, al")
                elif oper == "OP_QMARK":
                    self.emit("    ; operador ? não implementado (custom)")

                # guarda resultado
                self.emit(f"    mov [mem+{self.tempmap[dst]}], rax")

            # -----------------------------------------------------
            # ASSIGN
            # -----------------------------------------------------
            elif op == "assign":
                _, dst, src = ins

                # aloca destino se não existir
                self.alloc(dst)

                self.emit(f"    ; {dst} = {src}")
                self.emit(f"    {self.operand(src)}")
                self.emit("    pop rax")
                self.emit(f"    mov [mem+{self.varmap[dst]}], rax")

            # -----------------------------------------------------
            # ALLOC
            # -----------------------------------------------------
            elif op == "alloc":
                _, name = ins
                self.alloc(name)
                self.emit(f"    ; alloc {name} @ mem+{self.varmap[name]}")

            # -----------------------------------------------------
            # INPUT
            # -----------------------------------------------------
            elif op == "read":
                _, name = ins
                self.alloc(name)
                self.emit("    ; read")
                self.emit("    call read_int")
                self.emit(f"    mov [mem+{self.varmap[name]}], rax")

            # -----------------------------------------------------
            # OUTPUT
            # -----------------------------------------------------
            elif op == "print":
                _, val = ins
                self.emit("    ; print")
                self.emit(f"    {self.operand(val)}")
                self.emit("    pop rax")
                self.emit("    call print_int")

            # -----------------------------------------------------
            # RETURN
            # -----------------------------------------------------
            elif op == "ret":
                _, val = ins
                self.emit("    ; return")
                self.emit(f"    {self.operand(val)}")
                self.emit("    pop rax")

            # -----------------------------------------------------
            # COMMENT
            # -----------------------------------------------------
            elif op == "comment":
                _, text = ins
                self.emit(f"    ; {text}")

            else:
                self.emit(f"    ; UNKNOWN INSTR {ins}")

        return "\n".join(self.asm)
