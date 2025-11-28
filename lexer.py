import ply.lex as lex

# Lista completa de tokens
tokens = [
    # Palavras-chave
    "KW_INT", "KW_FLOAT", "KW_CHAR", "KW_FUNCTION",
    "KW_MAIN", "KW_BEGIN", "KW_WHILE", "KW_END",

    # Literais
    "NUM_INT", "STRING_DQ", "STRING_SQ", "ID",

    # Operadores
    "OP_EQ", "OP_NE", "OP_ARROW",
    "OP_LT", "OP_GT", "OP_ADD", "OP_SUB",
    "OP_MUL", "OP_DIV", "OP_ASSIGN", "OP_QMARK",

    # Símbolos
    "SEMI", "COMMA", "COLON",
    "LPAREN", "RPAREN", "LBRACE", "RBRACE",
]

# Estados
states = (
    ('COMMENT', 'exclusive'),
    ('AFTEREND', 'exclusive'),
)

# Função utilitária
def tk(name, t):
    print(f"<{name},{t.value}>")
    return t

# IGNORAR espaço/tab/nova linha
t_ignore = " \t\r\n"

# ---------------------------
# ESTADO: COMENTÁRIO
# ---------------------------

# Entrada no estado COMMENT
def t_COMMENT_enter(t):
    r"/:"
    t.lexer.begin("COMMENT")

# Fim do comentário
def t_COMMENT_end(t):
    r":/"
    t.lexer.begin("INITIAL")

# Ignorar tudo dentro do comentário
t_COMMENT_ignore = " \t\r\n"

# Consumir qualquer outro caractere dentro do comentário
def t_COMMENT_any(t):
    r"."
    pass

# Erro dentro do comentário
def t_COMMENT_error(t):
    t.lexer.skip(1)

t_ignore_COMMENT = " \t\r\n"


# ---------------------------
# ESTADO: AFTEREND
# ---------------------------

# Ignorar tudo após END
t_AFTEREND_ignore = " \t\r\n"

def t_AFTEREND_any(t):
    r"."
    pass

def t_AFTEREND_error(t):
    t.lexer.skip(1)


# ===================================
# PALAVRAS-CHAVE
# ===================================
def t_KW_INT(t):
    r"INT"
    return tk("KW_INT", t)

def t_KW_FLOAT(t):
    r"FLOAT"
    return tk("KW_FLOAT", t)

def t_KW_CHAR(t):
    r"CHAR"
    return tk("KW_CHAR", t)

def t_KW_FUNCTION(t):
    r"FUNCTION"
    return tk("KW_FUNCTION", t)

def t_KW_MAIN(t):
    r"MAIN"
    return tk("KW_MAIN", t)

def t_KW_BEGIN(t):
    r"BEGIN"
    return tk("KW_BEGIN", t)

def t_KW_WHILE(t):
    r"WHILE"
    return tk("KW_WHILE", t)

def t_KW_END(t):
    r"END"
    t.lexer.begin("AFTEREND")
    return tk("KW_END", t)


# ===================================
# LITERAIS
# ===================================
def t_NUM_INT(t):
    r"(0|[1-9][0-9]*)"
    return tk("NUM_INT", t)

def t_STRING_DQ(t):
    r'"([^"\\]|\\.)*"'
    return tk("STRING_DQ", t)

def t_STRING_SQ(t):
    r"'([^'\\]|\\.)*'"
    return tk("STRING_SQ", t)

def t_ID(t):
    r"[A-Z][A-Z-]*"
    return tk("ID", t)


# ===================================
# OPERADORES
# ===================================
def t_OP_EQ(t):
    r"=="
    return tk("OP_EQ", t)

def t_OP_NE(t):
    r"!="
    return tk("OP_NE", t)

def t_OP_ARROW(t):
    r"->"
    return tk("OP_ARROW", t)

def t_OP_LT(t):
    r"<"
    return tk("OP_LT", t)

def t_OP_GT(t):
    r">"
    return tk("OP_GT", t)

def t_OP_ADD(t):
    r"\+"
    return tk("OP_ADD", t)

def t_OP_SUB(t):
    r"-"
    return tk("OP_SUB", t)

def t_OP_MUL(t):
    r"\*"
    return tk("OP_MUL", t)

def t_OP_DIV(t):
    r"/"
    return tk("OP_DIV", t)

def t_OP_ASSIGN(t):
    r"="
    return tk("OP_ASSIGN", t)

def t_OP_QMARK(t):
    r"\?"
    return tk("OP_QMARK", t)


# ===================================
# SÍMBOLOS
# ===================================
def t_SEMI(t):
    r";"
    return tk("SEMI", t)

def t_COMMA(t):
    r","
    return tk("COMMA", t)

def t_COLON(t):
    r":"
    return tk("COLON", t)

def t_LPAREN(t):
    r"\("
    return tk("LPAREN", t)

def t_RPAREN(t):
    r"\)"
    return tk("RPAREN", t)

def t_LBRACE(t):
    r"\{"
    return tk("LBRACE", t)

def t_RBRACE(t):
    r"\}"
    return tk("RBRACE", t)


# ---------------------------
# ERROS GERAIS
# ---------------------------
def t_error(t):
    print(f"[line {t.lineno}] invalid_char: {t.value[0]}")
    t.lexer.skip(1)


# ---------------------------
# CONSTRUÇÃO DO LÉXER
# ---------------------------
lexer = lex.lex(reflags=0)
