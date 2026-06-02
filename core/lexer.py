# Lexer
# -----

from dataclasses import dataclass
from typing import Any

from core.types import *
from core.errors import *

# ==========================================
# LEXER
# ==========================================

@dataclass
class Token:
    __slots__ = ('type', 'value', 'line', 'col')
    type: TokenType
    value: Any
    line: int
    col: int

class Lexer:
    def __init__(self, source_code, start_line=1, start_col=1):
        self.source = source_code
        self.pos = 0
        self.line = start_line
        self.col = start_col
        self.current_char = self.source[0] if self.source else None

    def advance(self):
        if self.current_char == '\n':
            self.line += 1
            self.col = 0
        
        self.pos += 1
        self.col += 1
        
        if self.pos < len(self.source):
            self.current_char = self.source[self.pos]
        else:
            self.current_char = None

    def peek(self):
        peek_pos = self.pos + 1
        if peek_pos < len(self.source):
            return self.source[peek_pos]
        return None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def skip_comment(self):
        while self.current_char is not None and self.current_char != '\n':
            self.advance()
        self.advance()

    def skip_multiline_comment(self):
        while self.current_char is not None:
            if self.current_char == '*' and self.peek() == '~':
                self.advance()
                self.advance()
                break
            self.advance()
    
    def make_identifier(self):
        match = RE_ID.match(self.source, self.pos)
        if match:
            id_str = match.group(0)
            start_col = self.col
            
            # Update Lexer state
            self.pos += len(id_str)
            self.col += len(id_str)
            if self.pos < len(self.source):
                self.current_char = self.source[self.pos]
            else:
                self.current_char = None
            
            # Keyword Logic
            if id_str == 'and': return Token(TOKEN_AND, 'and', self.line, start_col)
            if id_str == 'or': return Token(TOKEN_OR, 'or', self.line, start_col)
            if id_str == 'not': return Token(TOKEN_NOT, 'not', self.line, start_col)
            if id_str == 'is': return Token(TOKEN_IS, 'is', self.line, start_col)
            if id_str in KEYWORDS: return Token(TOKEN_KEYWORD, id_str, self.line, start_col)
            
            return Token(TOKEN_ID, id_str, self.line, start_col)
        
        # Fallback should technically never happen if called correctly
        return Token(TOKEN_EOF, None, self.line, self.col)

    def make_number(self):
        match = RE_NUMBER.match(self.source, self.pos)
        if match:
            num_str = match.group(0)
            start_col = self.col
            
            self.pos += len(num_str)
            self.col += len(num_str)
            if self.pos < len(self.source):
                self.current_char = self.source[self.pos]
            else:
                self.current_char = None
            
            if '.' in num_str:
                return Token(TOKEN_FLOAT, float(num_str), self.line, start_col)
            return Token(TOKEN_INT, int(num_str), self.line, start_col)
            
        return Token(TOKEN_EOF, None, self.line, self.col)

    def make_string(self):
        start_col = self.col
        start_line = self.line
        quote = self.current_char
        self.advance()
        s = ''
        escape_map = {
            'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'",
            'b': '\b', 'h': '\t', '0': '\0'
        }
        
        while self.current_char is not None and self.current_char != quote:
            if self.current_char == '\\':
                self.advance()
                
                if self.current_char == 'u':
                    self.advance()
                    hex_str = ''
                    for _ in range(4):
                        if self.current_char is None:
                             raise lunite_error("Syntax", "Unterminated Unicode escape sequence", self.line, self.col)
                        if self.current_char not in "0123456789abcdefABCDEF":
                             raise lunite_error("Syntax", f"Invalid Unicode hex character '{self.current_char}'", self.line, self.col)
                        hex_str += self.current_char
                        self.advance()
                    try:
                        s += chr(int(hex_str, 16))
                    except ValueError:
                         raise lunite_error("Syntax", f"Invalid Unicode sequence '\\u{hex_str}'", self.line, self.col)
                    continue 

                elif self.current_char in escape_map:
                    s += escape_map[self.current_char]
                else:
                    s += '\\' 
                    if self.current_char:
                        s += self.current_char
            else:
                s += self.current_char
            
            self.advance()

        if self.current_char is None:
            raise lunite_error("Syntax", "Unterminated string literal", start_line, start_col)
            
        self.advance()
        
        if quote == "'":
            if len(s) != 1:
                raise lunite_error("Syntax", "Char literal must be length 1.", start_line, start_col)
            return Token(TOKEN_CHAR, s, start_line, start_col)
            
        return Token(TOKEN_STRING, s, start_line, start_col)
    
    def make_fstring(self):
        start_col = self.col
        start_line = self.line
        self.advance()
        self.advance()
        
        raw_s = ""
        brace_depth = 0
        
        while self.current_char is not None:
            char = self.current_char
            
            if char == '"' and brace_depth == 0:
                self.advance()
                return Token(TOKEN_FSTRING, raw_s, start_line, start_col)
            
            if char == '{':
                brace_depth += 1
            elif char == '}':
                if brace_depth > 0: brace_depth -= 1
            
            if char == '\\':
                raw_s += char
                self.advance()
                if self.current_char is not None:
                    raw_s += self.current_char
                    self.advance()
                continue
            
            raw_s += char
            self.advance()
        
        raise lunite_error("Syntax", "Unterminated f-string", start_line, start_col)

    def get_next_token(self):
        while self.current_char is not None:
            start_col = self.col 
            
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            if self.current_char == '~':
                peek_char = self.peek()
                if peek_char == '~':
                    self.advance(); self.advance()
                    self.skip_comment()
                    continue
                elif peek_char == '*':
                    self.advance(); self.advance()
                    self.skip_multiline_comment()
                    continue
                else:
                    self.advance()
                    return Token(TOKEN_BIT_NOT, '~', self.line, start_col)

            if self.current_char == '/':
                peek = self.peek()
                if peek == '=':
                    self.advance(); self.advance()
                    return Token(TOKEN_DIVEQ, '/=', self.line, start_col)
                else:
                    self.advance()
                    return Token(TOKEN_DIV, '/', self.line, start_col)

            if self.current_char == '&':
                self.advance()
                if self.current_char == '&':
                    self.advance()
                    return Token(TOKEN_AND, '&&', self.line, start_col)
                return Token(TOKEN_BIT_AND, '&', self.line, start_col)

            if self.current_char == '|':
                self.advance()
                if self.current_char == '|':
                    self.advance()
                    return Token(TOKEN_OR, '||', self.line, start_col)
                return Token(TOKEN_BIT_OR, '|', self.line, start_col)

            if self.current_char == '^':
                self.advance()
                return Token(TOKEN_BIT_XOR, '^', self.line, start_col)

            if self.current_char == '<':
                self.advance()
                if self.current_char == '<':
                    self.advance()
                    return Token(TOKEN_LSHIFT, '<<', self.line, start_col)
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_LE, '<=', self.line, start_col)
                return Token(TOKEN_LT, '<', self.line, start_col)

            if self.current_char == '>':
                self.advance()
                if self.current_char == '>':
                    self.advance()
                    return Token(TOKEN_RSHIFT, '>>', self.line, start_col)
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_GE, '>=', self.line, start_col)
                return Token(TOKEN_GT, '>', self.line, start_col)

            if self.current_char == 'f' and self.peek() == '"':
                return self.make_fstring()

            if self.current_char.isalpha() or self.current_char == '_':
                return self.make_identifier()
            
            if self.current_char.isdigit():
                return self.make_number()

            if self.current_char == '.':
                if self.peek() is not None and self.peek().isdigit():
                     return self.make_number()
                self.advance()
                return Token(TOKEN_DOT, '.', self.line, start_col)
            
            if self.current_char == '"' or self.current_char == "'":
                return self.make_string()
            
            if self.current_char == '+':
                self.advance()
                if self.current_char == '+':
                    self.advance()
                    return Token(TOKEN_INC, '++', self.line, start_col)
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_PLUSEQ, '+=', self.line, start_col)
                return Token(TOKEN_PLUS, '+', self.line, start_col)

            if self.current_char == '-':
                self.advance()
                if self.current_char == '-':
                    self.advance()
                    return Token(TOKEN_DEC, '--', self.line, start_col)
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_MINUSEQ, '-=', self.line, start_col)
                return Token(TOKEN_MINUS, '-', self.line, start_col)

            if self.current_char == '*':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_MULEQ, '*=', self.line, start_col)
                return Token(TOKEN_MUL, '*', self.line, start_col)
            
            if self.current_char == '%':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_MODEQ, '%=', self.line, start_col)
                return Token(TOKEN_MOD, '%', self.line, start_col)
            
            if self.current_char == '(':
                self.advance()
                return Token(TOKEN_LPAREN, '(', self.line, start_col)
            
            if self.current_char == ')':
                self.advance()
                return Token(TOKEN_RPAREN, ')', self.line, start_col)
            
            if self.current_char == '{':
                self.advance()
                return Token(TOKEN_LBRACE, '{', self.line, start_col)
            
            if self.current_char == '}':
                self.advance()
                return Token(TOKEN_RBRACE, '}', self.line, start_col)
            
            if self.current_char == '[':
                self.advance()
                return Token(TOKEN_LBRACKET, '[', self.line, start_col)
            
            if self.current_char == ']':
                self.advance()
                return Token(TOKEN_RBRACKET, ']', self.line, start_col)
            
            if self.current_char == ':':
                self.advance()
                return Token(TOKEN_COLON, ':', self.line, start_col)

            if self.current_char == ';':
                self.advance()
                return Token(TOKEN_SEMI, ';', self.line, start_col)
            
            if self.current_char == ',':
                self.advance()
                return Token(TOKEN_COMMA, ',', self.line, start_col)
            
            if self.current_char == '.':
                self.advance()
                return Token(TOKEN_DOT, '.', self.line, start_col)
            
            if self.current_char == '?':
                self.advance()
                return Token(TOKEN_QUESTION, '?', self.line, start_col)
            
            if self.current_char == '=':
                self.advance()
                if self.current_char == '>':
                    self.advance()
                    return Token(TOKEN_ARROW, '=>', self.line, start_col)
                if self.current_char == '=': 
                    self.advance()
                    return Token(TOKEN_EQ, '==', self.line, start_col)
                return Token(TOKEN_ASSIGN, '=', self.line, start_col)
            
            if self.current_char == '!':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_NEQ, '!=', self.line, start_col)
                return Token(TOKEN_NOT, '!', self.line, start_col)
            
            if self.current_char == '@':
                self.advance()
                return Token(TOKEN_AT, '@', self.line, start_col)
            
            raise lunite_error("Syntax", f"Illegal character '{self.current_char}", self.line, self.col)

        return Token(TOKEN_EOF, None, self.line, self.col)

    def __iter__(self):
        while True:
            token = self.get_next_token()
            yield token
            if token.type == TOKEN_EOF:
                break
