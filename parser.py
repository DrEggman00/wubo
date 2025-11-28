# parser.py
import ply.yacc as yacc
from lexer import tokens
from ast import (
    Program, Function, Block, Declaration, VarDecl, Assignment, Input, Output,
    While, Return, Comment, BinaryOp, Identifier, Number, StringLit, pretty_print
)

# -------------------------
# Precedência
# -------------------------
precedence = (
    ('left', 'OP_ADD', 'OP_SUB'),
    ('left', 'OP_MUL', 'OP_DIV'),
)

# -------------------------
# Erro
# -------------------------
def p_error(p):
    if p:
        print(f"Erro de sintaxe: token inesperado '{p.value}' na linha {p.lineno}")
    else:
        print("Erro de sintaxe: fim inesperado do arquivo")


# -------------------------
# Gramática -> construção de AST
# -------------------------

def p_programa(p):
    """programa : KW_BEGIN lista_funcoes KW_END"""
    # lista_funcoes retorna lista de funções
    p[0] = Program(p[2])

def p_lista_funcoes_empty(p):
    """lista_funcoes : """
    p[0] = []

def p_lista_funcoes_rec(p):
    """lista_funcoes : lista_funcoes funcao"""
    p[0] = p[1] + [p[2]]

def p_funcao(p):
    """funcao : KW_FUNCTION id_ou_main COLON bloco"""
    # id_ou_main retorna string (nome)
    p[0] = Function(p[2], p[4])

def p_id_ou_main(p):
    """id_ou_main : KW_MAIN
                  | ID
    """
    if p[1] == 'MAIN':
        p[0] = 'MAIN'
    else:
        p[0] = p[1]

def p_bloco(p):
    """bloco : lista_comandos"""
    p[0] = Block(p[1])

def p_lista_comandos_empty(p):
    """lista_comandos : """
    p[0] = []

def p_lista_comandos_rec(p):
    """lista_comandos : lista_comandos comando"""
    p[0] = p[1] + [p[2]]

def p_comando(p):
    """comando : declaracao
               | atribuicao
               | entrada
               | saida
               | while_stmt
               | retorno
               | comentario
    """
    p[0] = p[1]

def p_declaracao(p):
    """declaracao : tipo lista_decl SEMI"""
    # lista_decl -> list of VarDecl
    p[0] = Declaration(p[1], p[2])

def p_tipo(p):
    """tipo : KW_INT
            | KW_FLOAT
            | KW_CHAR
    """
    p[0] = p[1]  # token lexeme (INT/FLOAT/CHAR)

def p_lista_decl(p):
    """lista_decl : ID opt_init decl_cont"""
    # constrói um VarDecl e junta com decl_cont (que pode ser further list)
    first = VarDecl(p[1], p[2])
    if p[3] is None:
        p[0] = [first]
    else:
        # p[3] é lista de VarDecls
        p[0] = [first] + p[3]

def p_decl_cont_empty(p):
    """decl_cont : """
    p[0] = None

def p_decl_cont_rec(p):
    """decl_cont : COMMA lista_decl"""
    # lista_decl já é lista
    p[0] = p[2]

def p_opt_init_empty(p):
    """opt_init : """
    p[0] = None

def p_opt_init_assign(p):
    """opt_init : OP_ASSIGN expressao"""
    p[0] = p[2]

def p_atribuicao(p):
    """atribuicao : ID OP_ASSIGN expressao SEMI"""
    p[0] = Assignment(p[1], p[3])

def p_entrada(p):
    """entrada : INPUT ID SEMI"""
    p[0] = Input(p[2])

def p_saida(p):
    """saida : OUTPUT expressao SEMI"""
    p[0] = Output(p[2])

def p_while_stmt(p):
    """while_stmt : KW_WHILE LPAREN expressao RPAREN LBRACE bloco RBRACE"""
    p[0] = While(p[3], p[6])

def p_retorno(p):
    """retorno : RETURN expressao SEMI"""
    p[0] = Return(p[2])

def p_comentario(p):
    """comentario : COMMENT"""
    p[0] = Comment(p[1])


# EXPRESSAO: suportamos recursão binária (esquerda-associativa)
def p_expressao_termo(p):
    """expressao : termo"""
    p[0] = p[1]

def p_expressao_binaria(p):
    """expressao : expressao operador termo"""
    p[0] = BinaryOp(p[1], p[2], p[3])

def p_termo(p):
    """termo : ID
             | NUM_INT
             | STRING_DQ
             | STRING_SQ
    """
    tok = p[1]
    # NUM_INT vem como lexema (e.g. "123"), STRING_* mantém as aspas - você pode strip quando quiser
    if isinstance(tok, str):
        # ID or lexeme strings
        # Decide by token type via p.slice[1].type
        ttype = p.slice[1].type
        if ttype == 'ID':
            p[0] = Identifier(tok)
        elif ttype == 'NUM_INT':
            p[0] = Number(tok)
        else:  # STRING_DQ or STRING_SQ
            p[0] = StringLit(tok)
    else:
        # fallback
        p[0] = Identifier(str(tok))


def p_operador(p):
    """operador : OP_ADD
                | OP_SUB
                | OP_MUL
                | OP_DIV
                | OP_EQ
                | OP_NE
                | OP_LT
                | OP_GT
                | OP_QMARK
    """
    p[0] = p[1]  # operador como string (lexema)


# -------------------------
# Construção do parser
# -------------------------
parser = yacc.yacc()

# -------------------------
# Helper para parse e retornar AST
# -------------------------
def parse(data: str):
    return parser.parse(data, lexer=None)  # lexer from lexer.py will be used automatically


# -------------------------
# Execução direta (exemplo)
# -------------------------
if __name__ == "__main__":
    import sys
    data = sys.stdin.read()
    ast_root = parse(data)
    if ast_root:
        pretty_print(ast_root)
    else:
        print("Nenhuma AST gerada (provavelmente erro de sintaxe).")
