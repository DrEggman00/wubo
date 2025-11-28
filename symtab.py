# ===============================
# Tipos e Kinds (equivalentes ao .h)
# ===============================

class Type:
    TYPE_INT = 1
    TYPE_FLOAT = 2
    TYPE_CHAR = 3


class Kind:
    KIND_VAR = 1
    KIND_FUNC = 2


# ===============================
# Estruturas de símbolo e escopo
# ===============================

class Symbol:
    def __init__(self, name, kind, type_, size=0, offset=0):
        self.name = name
        self.kind = kind
        self.type = type_
        self.size = size
        self.offset = offset
        self.param_count = 0
        self.frame_size = 0
        self.next = None  # para manter compatibilidade conceitual com C (lista encadeada)


class Scope:
    def __init__(self, name, parent=None, level=0):
        self.name = name
        self.symbols = None  # lista encadeada
        self.next_offset = 0
        self.parent = parent
        self.level = level


# ===============================
# Tabela de símbolos global
# ===============================

current_scope = None


# ===============================
# Funções auxiliares
# ===============================

def sizeof_type(t):
    if t == Type.TYPE_INT:
        return 4
    if t == Type.TYPE_FLOAT:
        return 8
    if t == Type.TYPE_CHAR:
        return 1
    return 0


# ===============================
# Inicialização e gerenciamento de escopos
# ===============================

def symtab_init():
    global current_scope
    if current_scope is not None:
        return
    current_scope = Scope("<global>", parent=None, level=0)


def symtab_free():
    global current_scope
    while current_scope is not None:
        current_scope = current_scope.parent


def enter_scope(name="<anon>"):
    global current_scope
    s = Scope(name, parent=current_scope,
              level=(current_scope.level + 1 if current_scope else 0))
    current_scope = s


def exit_scope():
    global current_scope
    if current_scope:
        current_scope = current_scope.parent


# ===============================
# Busca
# ===============================

def _find_in_scope(scope, name):
    sym = scope.symbols
    while sym:
        if sym.name == name:
            return sym
        sym = sym.next
    return None


def lookup(name):
    s = current_scope
    while s:
        found = _find_in_scope(s, name)
        if found:
            return found
        s = s.parent
    return None


# ===============================
# Inserções
# ===============================

def insert_var(name, type_):
    global current_scope

    if current_scope is None:
        symtab_init()

    if _find_in_scope(current_scope, name):
        return -1  # redeclaração no mesmo escopo

    size = sizeof_type(type_)
    offset = current_scope.next_offset

    sym = Symbol(name, Kind.KIND_VAR, type_, size=size, offset=offset)
    sym.next = current_scope.symbols
    current_scope.symbols = sym

    current_scope.next_offset += size
    return offset


def insert_param(name, type_):
    global current_scope

    if current_scope is None:
        return -1
    if _find_in_scope(current_scope, name):
        return -1

    size = sizeof_type(type_)
    offset = current_scope.next_offset

    sym = Symbol(name, Kind.KIND_VAR, type_, size=size, offset=offset)
    sym.next = current_scope.symbols
    current_scope.symbols = sym

    current_scope.next_offset += size
    return offset


def insert_func(name, return_type):
    global current_scope

    if current_scope is None:
        symtab_init()

    # Função só vai para o escopo global
    target = current_scope
    while target.parent:
        target = target.parent

    if _find_in_scope(target, name):
        return -1

    sym = Symbol(name, Kind.KIND_FUNC, return_type, size=0, offset=0)
    sym.next = target.symbols
    target.symbols = sym

    return 0


# ===============================
# Impressão de Debug
# ===============================

def symtab_print_current():
    if not current_scope:
        print("<sem escopo>")
        return

    print(f"Escopo '{current_scope.name}' (level={current_scope.level}) - next_offset={current_scope.next_offset}")
    sym = current_scope.symbols
    while sym:
        kind = "FUNC" if sym.kind == Kind.KIND_FUNC else "VAR"
        print(f"  {sym.name}: kind={kind} type={sym.type} size={sym.size} offset={sym.offset} params={sym.param_count} frame={sym.frame_size}")
        sym = sym.next


def symtab_print_all():
    s = current_scope
    while s:
        print("---")
        print(f"Escopo '{s.name}' (level={s.level}) - next_offset={s.next_offset}")
        sym = s.symbols
        while sym:
            kind = "FUNC" if sym.kind == Kind.KIND_FUNC else "VAR"
            print(f"  {sym.name}: kind={kind} type={sym.type} size={sym.size} offset={sym.offset} params={sym.param_count} frame={sym.frame_size}")
            sym = sym.next
        s = s.parent
