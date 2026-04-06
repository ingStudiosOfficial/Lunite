# Constants
# ---------

import re

# ==========================================
# VERSION & CONFIG
# ==========================================

LUNITE_VERSION_STR = "v1.9.7"
COPYRIGHT          = "Copyright ANW, 2025-2026"
LUNITE_USER_AGENT  = "Lunite/1.9.7"
CURRENT_FILE       = "REPL"

# ==========================================
# PRE-COMPILED REGEX
# ==========================================

RE_NUMBER = re.compile(r'(\d+(\.\d*)?|\.\d+)')
RE_ID     = re.compile(r'[a-zA-Z_]\w*')

# ==========================================
# TOKENS LIST
# ==========================================

TokenType      = str
TOKEN_INT      = 'INT'
TOKEN_FLOAT    = 'FLOAT'
TOKEN_STRING   = 'STRING'
TOKEN_CHAR     = 'CHAR'
TOKEN_ID       = 'ID'
TOKEN_KEYWORD  = 'KEYWORD'
TOKEN_PLUS     = 'PLUS'
TOKEN_MINUS    = 'MINUS'
TOKEN_MUL      = 'MUL'
TOKEN_DIV      = 'DIV'
TOKEN_MOD      = 'MOD'
TOKEN_LPAREN   = 'LPAREN'
TOKEN_RPAREN   = 'RPAREN'
TOKEN_LBRACE   = 'LBRACE'
TOKEN_RBRACE   = 'RBRACE'
TOKEN_LBRACKET = 'LBRACKET'
TOKEN_RBRACKET = 'RBRACKET'
TOKEN_COLON    = 'COLON'
TOKEN_COMMA    = 'COMMA'
TOKEN_ASSIGN   = 'ASSIGN'
TOKEN_EQ       = 'EQ'
TOKEN_NEQ      = 'NEQ'
TOKEN_GT       = 'GT'
TOKEN_LT       = 'LT'
TOKEN_GE       = 'GE'
TOKEN_LE       = 'LE'
TOKEN_EOF      = 'EOF'
TOKEN_DOT      = 'DOT'
TOKEN_QUESTION = 'QUESTION'
TOKEN_BIT_AND  = 'BIT_AND'
TOKEN_BIT_OR   = 'BIT_OR'
TOKEN_BIT_XOR  = 'BIT_XOR'
TOKEN_BIT_NOT  = 'BIT_NOT'
TOKEN_LSHIFT   = 'LSHIFT'
TOKEN_RSHIFT   = 'RSHIFT'
TOKEN_PLUSEQ   = 'PLUSEQ'
TOKEN_MINUSEQ  = 'MINUSEQ'
TOKEN_MULEQ    = 'MULEQ'
TOKEN_DIVEQ    = 'DIVEQ'
TOKEN_MODEQ    = 'MODEQ'
TOKEN_AND      = 'AND'
TOKEN_OR       = 'OR'
TOKEN_NOT      = 'NOT'
TOKEN_FSTRING  = 'FSTRING'
TOKEN_ARROW    = 'ARROW'
TOKEN_IS       = 'IS'
TOKEN_SEMI     = 'SEMI'
TOKEN_INC      = 'INC'
TOKEN_DEC      = 'DEC'
TOKEN_AT       = 'AT'

# ==========================================
# KEYWORDS LIST
# ==========================================

KEYWORDS = [
    'let', 'func', 'class', 'if', 'else', 'while', 'for', 'in',
    'return', 'new', 'true', 'false', 'null', 'import',
    'attempt', 'rescue', 'finally', 'extends', 'break', 'advance', 'leap',
    'match', 'other', 'and', 'or', 'not', 'const', 'import_py',
    'enum', 'is', 'from', 'assert', 'public', 'private', 'global',
    'async', 'await', 'macro'
]