#!/usr/bin/env python3
# /== == == == == == == == == == ==\
# |==  LUNITE - v1.8.0 - by ANW  ==|
# \== == == == == == == == == == ==/

import sys
import os
import re
import shutil
import platform
import subprocess
import json
import urllib.request
import importlib
import datetime
import math
import time
import random
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Tuple, Set

# ==========================================
# VERSION & CONFIG
# ==========================================

LUNITE_VERSION_STR = "v1.8.0"
COPYRIGHT          = "Copyright ANW, 2025"
LUNITE_USER_AGENT  = "Lunite/1.8.0"

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
TOKEN_AND      = 'AND'
TOKEN_OR       = 'OR'
TOKEN_NOT      = 'NOT'
TOKEN_FSTRING  = 'FSTRING'
TOKEN_ARROW    = 'ARROW'
TOKEN_IS       = 'IS'

# ==========================================
# KEYWORDS LIST
# ==========================================

KEYWORDS = [
    'let', 'func', 'class', 'if', 'else', 'while', 'for', 'in',
    'return', 'new', 'true', 'false', 'null', 'import',
    'attempt', 'rescue', 'extends', 'break', 'advance', 'leap',
    'match', 'other', 'and', 'or', 'not', 'const', 'import_py',
    'enum', 'is'
]

# ==========================================
# RUNTIME DATA TYPE WRAPPERS
# ==========================================
class LBit(int):
    def __new__(cls, value):
        val = int(value)
        if val not in (0, 1):
            raise ValueError("The Bit data type must be 0 or 1")
        return super().__new__(cls, val)
    def __repr__(self): return f"{int(self)}"

class LByte(int):
    def __new__(cls, value):
        val = int(value)
        if val < 0 or val > 255:
            raise ValueError("The Byte data type must be 0 to 255")
        return super().__new__(cls, val)
    def __repr__(self): return f"{int(self)}"

class LChar(str):
    def __new__(cls, value):
        if len(value) != 1:
            raise ValueError("The Char data type must be exactly of length 1")
        return super().__new__(cls, value)
    def __repr__(self): return f"'{self}'"

# ==========================================
# LEXER
# ==========================================

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int

class Lexer:
    def __init__(self, source_code):
        self.source = source_code
        self.pos = 0
        self.line = 1
        self.current_char = self.source[0] if self.source else None

    def advance(self):
        self.pos += 1
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
            if self.current_char == '\n':
                self.line += 1
            self.advance()

    def skip_comment(self):
        while self.current_char is not None and self.current_char != '\n':
            self.advance()
        self.advance() # Skip newline
        self.line += 1

    def skip_multiline_comment(self):
        while self.current_char is not None:
            if self.current_char == '*' and self.peek() == '~':
                self.advance() # consume *
                self.advance() # consume ~
                break
            if self.current_char == '\n':
                self.line += 1
            self.advance()

    def make_identifier(self):
        id_str = ''
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            id_str += self.current_char
            self.advance()
        
        if id_str == 'and':
            return Token(TOKEN_AND, 'and', self.line)
        if id_str == 'or':
            return Token(TOKEN_OR, 'or', self.line)
        if id_str == 'not':
            return Token(TOKEN_NOT, 'not', self.line)
        if id_str == 'is':
            return Token(TOKEN_IS, 'is', self.line)

        if id_str in KEYWORDS:
            return Token(TOKEN_KEYWORD, id_str, self.line)
            
        return Token(TOKEN_ID, id_str, self.line)

    def make_number(self):
        num_str = ''
        dot_count = 0
        
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '.'):
            if self.current_char == '.':
                if dot_count == 1: 
                    break
                
                dot_count += 1
                num_str += '.'
            else:
                num_str += self.current_char
            self.advance()
        
        if dot_count == 0:
            return Token(TOKEN_INT, int(num_str), self.line)
        else:
            return Token(TOKEN_FLOAT, float(num_str), self.line)

    def make_string(self):
        quote = self.current_char
        self.advance()
        s = ''
        escape_map = {
            'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'"
        }
        
        while self.current_char is not None and self.current_char != quote:
            if self.current_char == '\\':
                self.advance()
                if self.current_char in escape_map:
                    s += escape_map[self.current_char]
                else:
                    s += '\\' 
                    if self.current_char:
                        s += self.current_char
            else:
                s += self.current_char
            self.advance()
            
        self.advance() # Close quote
        
        if quote == "'":
            if len(s) != 1:
                raise Exception(f"Syntax Error: Char literal '{s}' must be exactly of length 1.")
            return Token(TOKEN_CHAR, s, self.line)
            
        return Token(TOKEN_STRING, s, self.line)
    
    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            if self.current_char == '~':
                peek_char = self.peek()
                
                if peek_char == '~':
                    self.advance()
                    self.advance()
                    self.skip_comment()
                    continue
                
                elif peek_char == '*':
                    self.advance()
                    self.advance()
                    self.skip_multiline_comment()
                    continue
                
                else:
                    self.advance()
                    return Token(TOKEN_BIT_NOT, '~', self.line)

            if self.current_char == '/':
                peek = self.peek()
                if peek == '=':
                    self.advance(); self.advance()
                    return Token(TOKEN_DIVEQ, '/=', self.line)
                else:
                    self.advance()
                    return Token(TOKEN_DIV, '/', self.line)

            if self.current_char == '&':
                self.advance()
                if self.current_char == '&':
                    self.advance()
                    return Token(TOKEN_AND, '&&', self.line)
                return Token(TOKEN_BIT_AND, '&', self.line)

            if self.current_char == '|':
                self.advance()
                if self.current_char == '|':
                    self.advance()
                    return Token(TOKEN_OR, '||', self.line)
                return Token(TOKEN_BIT_OR, '|', self.line)

            if self.current_char == '^':
                self.advance()
                return Token(TOKEN_BIT_XOR, '^', self.line)

            if self.current_char == '<':
                self.advance()
                if self.current_char == '<':
                    self.advance()
                    return Token(TOKEN_LSHIFT, '<<', self.line)
                return Token(TOKEN_LT, '<', self.line)

            if self.current_char == '>':
                self.advance()
                if self.current_char == '>':
                    self.advance()
                    return Token(TOKEN_RSHIFT, '>>', self.line)
                return Token(TOKEN_GT, '>', self.line)

            if self.current_char == 'f' and self.peek() == '"':
                self.advance()
                token = self.make_string()
                token.type = TOKEN_FSTRING
                return token

            if self.current_char.isalpha() or self.current_char == '_':
                return self.make_identifier()
            
            if self.current_char.isdigit():
                return self.make_number()

            if self.current_char == '.':
                if self.peek() is not None and self.peek().isdigit():
                     return self.make_number()
                self.advance()
                return Token(TOKEN_DOT, '.', self.line)
            
            if self.current_char == '"' or self.current_char == "'":
                return self.make_string()
            
            if self.current_char == '+':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_PLUSEQ, '+=', self.line)
                return Token(TOKEN_PLUS, '+', self.line)

            if self.current_char == '-':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_MINUSEQ, '-=', self.line)
                return Token(TOKEN_MINUS, '-', self.line)

            if self.current_char == '*':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_MULEQ, '*=', self.line)
                return Token(TOKEN_MUL, '*', self.line)
            
            if self.current_char == '(':
                self.advance()
                return Token(TOKEN_LPAREN, '(', self.line)
            
            if self.current_char == ')':
                self.advance()
                return Token(TOKEN_RPAREN, ')', self.line)
            
            if self.current_char == '{':
                self.advance()
                return Token(TOKEN_LBRACE, '{', self.line)
            
            if self.current_char == '}':
                self.advance()
                return Token(TOKEN_RBRACE, '}', self.line)
            
            if self.current_char == '[':
                self.advance()
                return Token(TOKEN_LBRACKET, '[', self.line)
            
            if self.current_char == ']':
                self.advance()
                return Token(TOKEN_RBRACKET, ']', self.line)
            
            if self.current_char == ':':
                self.advance()
                return Token(TOKEN_COLON, ':', self.line)
            
            if self.current_char == ',':
                self.advance()
                return Token(TOKEN_COMMA, ',', self.line)
            
            if self.current_char == '.':
                self.advance()
                return Token(TOKEN_DOT, '.', self.line)
            
            if self.current_char == '?':
                self.advance()
                return Token(TOKEN_QUESTION, '?', self.line)
            
            if self.current_char == '=':
                self.advance()
                if self.current_char == '>':
                    self.advance()
                    return Token(TOKEN_ARROW, '=>', self.line)
                if self.current_char == '=': 
                    self.advance()
                    return Token(TOKEN_EQ, '==', self.line)
                return Token(TOKEN_ASSIGN, '=', self.line)
            
            if self.current_char == '=':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_EQ, '==', self.line)
                return Token(TOKEN_ASSIGN, '=', self.line)

            if self.current_char == '!':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return Token(TOKEN_NEQ, '!=', self.line)
                return Token(TOKEN_NOT, '!', self.line)
            
            raise Exception(f"Syntax Error: Illegal character '{self.current_char}' found at line {self.line}")

        return Token(TOKEN_EOF, None, self.line)
        
# ==========================================
# AST
# ==========================================

@dataclass
class AST:
    line: int = field(default=0, init=False)

@dataclass
class Number(AST):
    token: Token

@dataclass
class String(AST):
    token: Token

@dataclass
class Char(AST):
    token: Token

@dataclass
class Boolean(AST):
    token: Token
    value: bool

@dataclass
class Null(AST):
    pass

@dataclass
class ListLiteral(AST):
    elements: List[AST]

@dataclass
class DictLiteral(AST):
    pairs: List[Tuple[AST, AST]]

@dataclass
class Identifier(AST):
    token: Token

@dataclass
class UnaryOp(AST):
    op: Token
    expr: AST

@dataclass
class TernaryOp(AST):
    condition: AST
    true_expr: AST
    false_expr: AST

@dataclass
class BinaryOp(AST):
    left: AST
    op: Token
    right: AST

@dataclass
class Assign(AST):
    left: AST
    value: AST

@dataclass
class CompoundAssign(AST):
    left: AST
    op: Token
    value: AST

@dataclass
class Block(AST):
    statements: List[AST]

@dataclass
class FunctionDef(AST):
    name: str
    params: List[Tuple[str, Optional[AST]]]
    body: Block

@dataclass
class ClassDef(AST):
    name: str
    body: Block
    superclass: Optional[str]

@dataclass
class IfStatement(AST):
    condition: AST
    true_block: Block
    false_block: Optional[Block]

@dataclass
class WhileStatement(AST):
    condition: AST
    body: Block

@dataclass
class ForStatement(AST):
    iterator_name: str
    iterable: AST
    body: Block

@dataclass
class TryCatchStatement(AST):
    try_block: Block
    error_var: str
    catch_block: Block

@dataclass
class ImportStatement(AST):
    module_name: str

@dataclass
class FunctionCall(AST):
    name: str
    args: List[AST]

@dataclass
class MethodCall(AST):
    obj: AST
    method_name: str
    args: List[AST]

@dataclass
class MemberAccess(AST):
    obj: AST
    member_name: str

@dataclass
class IndexAccess(AST):
    target: AST
    index: AST

@dataclass
class ReturnStatement(AST):
    value: AST

@dataclass
class BreakStatement(AST):
    pass

@dataclass
class AdvanceStatement(AST):
    pass

@dataclass
class LeapStatement(AST):
    target: AST

@dataclass
class LabelDef(AST):
    name: str

@dataclass
class MatchCase(AST):
    value: AST
    body: Block

@dataclass
class MatchStatement(AST):
    subject: AST
    cases: List[MatchCase]
    default_block: Optional[Block]

@dataclass
class VarDecl(AST):
    name: str
    value: AST
    is_const: bool = False

@dataclass
class NewInstance(AST):
    class_name: str
    args: List[AST]

@dataclass
class ImportPyStatement(AST):
    module_name: str
    alias: str

@dataclass
class SetLiteral(AST):
    elements: List[AST]

@dataclass
class TupleLiteral(AST):
    elements: List[AST]

@dataclass
class EnumDef(AST):
    name: str
    members: List[str]

@dataclass
class LambdaExpr(AST):
    params: List[str]
    body: AST

@dataclass
class TypeCheckOp(AST):
    expr: AST
    target_type: AST

@dataclass
class DestructuringDecl(AST):
    names: List[str]
    value: AST
    is_const: bool = False

# ==========================================
# PARSER
# ==========================================

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos]
    
    def is_case_start(self):
        if self.pos + 1 >= len(self.tokens):
            return False
        
        curr = self.current_token.type
        next_t = self.tokens[self.pos + 1].type
        
        is_atom = curr in (TOKEN_INT, TOKEN_FLOAT, TOKEN_STRING, TOKEN_CHAR, TOKEN_ID, TOKEN_KEYWORD)

        if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'other':
            return False

        return is_atom and next_t == TOKEN_COLON

    def eat(self, token_type):
        if self.current_token.type == token_type:
            self.pos += 1
            if self.pos < len(self.tokens):
                self.current_token = self.tokens[self.pos]
        else:
            raise Exception(f"Syntax Error: Unexpected token of type {self.current_token.type}, expected type {token_type} at line {self.current_token.line}")

    def parse_args(self):
        args = []
        if self.current_token.type != TOKEN_RPAREN:
            args.append(self.expr())
            while self.current_token.type == TOKEN_COMMA:
                self.eat(TOKEN_COMMA)
                args.append(self.expr())
        return args

    def atom(self):
        token = self.current_token
        
        if token.type == TOKEN_INT or token.type == TOKEN_FLOAT:
            self.eat(token.type)
            return Number(token)
        
        elif token.type == TOKEN_CHAR:
            self.eat(TOKEN_CHAR)
            return Char(token)
        
        elif token.type == TOKEN_FSTRING:
            self.eat(TOKEN_FSTRING)
            pattern = r'\{([^}]+)\}'
            parts = re.split(pattern, token.value)
            
            root = String(Token(TOKEN_STRING, "", token.line))
            
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    if part:
                        lit = String(Token(TOKEN_STRING, part, token.line))
                        root = BinaryOp(root, Token(TOKEN_PLUS, '+', token.line), lit)
                else:
                    sub_lexer = Lexer(part)
                    sub_tokens = []
                    while True:
                        t = sub_lexer.get_next_token()
                        sub_tokens.append(t)
                        if t.type == TOKEN_EOF: break
                    
                    sub_parser = Parser(sub_tokens)
                    sub_expr = sub_parser.expr()
                    
                    str_call = FunctionCall('str', [sub_expr])
                    root = BinaryOp(root, Token(TOKEN_PLUS, '+', token.line), str_call)
            
            return root

        elif token.type == TOKEN_STRING:
            self.eat(TOKEN_STRING)
            return String(token)
        
        elif token.type == TOKEN_KEYWORD and token.value == 'true':
            self.eat(TOKEN_KEYWORD)
            return Boolean(token, True)
        
        elif token.type == TOKEN_KEYWORD and token.value == 'false':
            self.eat(TOKEN_KEYWORD)
            return Boolean(token, False)
        
        elif token.type == TOKEN_KEYWORD and token.value == 'null':
            self.eat(TOKEN_KEYWORD)
            return Null()
            
        elif token.type == TOKEN_LBRACKET:
            self.eat(TOKEN_LBRACKET)
            elements = []
            if self.current_token.type != TOKEN_RBRACKET:
                elements.append(self.expr())
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    elements.append(self.expr())
            self.eat(TOKEN_RBRACKET)
            return ListLiteral(elements)

        elif token.type == TOKEN_LBRACE:
            self.eat(TOKEN_LBRACE)
            if self.current_token.type == TOKEN_RBRACE:
                self.eat(TOKEN_RBRACE)
                return DictLiteral([])
            
            first = self.expr()
            
            if self.current_token.type == TOKEN_COLON:
                self.eat(TOKEN_COLON)
                val = self.expr()
                pairs = [(first, val)]
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    k = self.expr()
                    self.eat(TOKEN_COLON)
                    v = self.expr()
                    pairs.append((k, v))
                self.eat(TOKEN_RBRACE)
                return DictLiteral(pairs)
            else:
                elements = [first]
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    elements.append(self.expr())
                self.eat(TOKEN_RBRACE)
                return SetLiteral(elements)

        elif token.type == TOKEN_KEYWORD and token.value == 'new':
            self.eat(TOKEN_KEYWORD)
            class_name = self.current_token.value
            self.eat(TOKEN_ID)
            self.eat(TOKEN_LPAREN)
            args = self.parse_args()
            self.eat(TOKEN_RPAREN)
            return NewInstance(class_name, args)
        
        elif token.type == TOKEN_KEYWORD and token.value == 'in':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            args = self.parse_args()
            self.eat(TOKEN_RPAREN)
            return FunctionCall('in', args)

        elif token.type == TOKEN_ID:
            name = token.value
            self.eat(TOKEN_ID)
            if self.current_token.type == TOKEN_LPAREN:
                self.eat(TOKEN_LPAREN)
                args = self.parse_args()
                self.eat(TOKEN_RPAREN)
                return FunctionCall(name, args)
            return Identifier(token)
        
        elif token.type == TOKEN_LPAREN:
            self.eat(TOKEN_LPAREN)
            
            if self.current_token.type == TOKEN_RPAREN:
                self.eat(TOKEN_RPAREN)
                if self.current_token.type == TOKEN_ARROW:
                    self.eat(TOKEN_ARROW)
                    if self.current_token.type == TOKEN_LBRACE:
                        self.eat(TOKEN_LBRACE)
                        body = self.block()
                        self.eat(TOKEN_RBRACE)
                        return LambdaExpr([], body)
                    else:
                        expr = self.expr()
                        return LambdaExpr([], expr)
                return TupleLiteral([])
            
            exprs = []
            exprs.append(self.expr())
            while self.current_token.type == TOKEN_COMMA:
                self.eat(TOKEN_COMMA)
                if self.current_token.type != TOKEN_RPAREN:
                    exprs.append(self.expr())
            
            self.eat(TOKEN_RPAREN)
            
            if self.current_token.type == TOKEN_ARROW:
                self.eat(TOKEN_ARROW)
                
                params = []
                for e in exprs:
                    if isinstance(e, Identifier):
                        params.append(e.token.value)
                    else:
                        raise Exception("Syntax Error: Lambda parameters must be identifiers")
                
                if self.current_token.type == TOKEN_LBRACE:
                    self.eat(TOKEN_LBRACE)
                    body = self.block()
                    self.eat(TOKEN_RBRACE)
                    return LambdaExpr(params, body)
                else:
                    return LambdaExpr(params, self.expr())

            if len(exprs) == 1: return exprs[0]
            return TupleLiteral(exprs)
        
        raise Exception(f"Syntax Error: Invalid atom {token.value} found at line {token.line}")

    def factor(self):
        token = self.current_token
        
        if token.type in (TOKEN_PLUS, TOKEN_MINUS, TOKEN_BIT_NOT, TOKEN_NOT):
            self.eat(token.type)
            node = UnaryOp(op=token, expr=self.factor())
            return node

        node = self.atom()
        
        while self.current_token.type in (TOKEN_DOT, TOKEN_LBRACKET):
            if self.current_token.type == TOKEN_DOT:
                self.eat(TOKEN_DOT)
                member_name = self.current_token.value
                self.eat(TOKEN_ID)
                if self.current_token.type == TOKEN_LPAREN:
                    self.eat(TOKEN_LPAREN)
                    args = self.parse_args()
                    self.eat(TOKEN_RPAREN)
                    node = MethodCall(node, member_name, args)
                else:
                    node = MemberAccess(node, member_name)
            
            elif self.current_token.type == TOKEN_LBRACKET:
                self.eat(TOKEN_LBRACKET)
                index = self.expr()
                self.eat(TOKEN_RBRACKET)
                node = IndexAccess(node, index)
        
        return node

    def term(self):
        node = self.factor()
        while self.current_token.type in (TOKEN_MUL, TOKEN_DIV):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.factor())
        return node
    
    def math_expr(self):
        node = self.term()
        while self.current_token.type in (TOKEN_PLUS, TOKEN_MINUS):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.term())
        return node
    
    def shift_expr(self):
        node = self.math_expr()
        while self.current_token.type in (TOKEN_LSHIFT, TOKEN_RSHIFT):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.math_expr())
        return node
    
    def bitwise_expr(self):
        node = self.shift_expr()
        while self.current_token.type in (TOKEN_BIT_AND, TOKEN_BIT_OR, TOKEN_BIT_XOR):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.shift_expr())
        return node
    
    def comp_expr(self):
        node = self.bitwise_expr()
        while self.current_token.type in (TOKEN_EQ, TOKEN_NEQ, TOKEN_GT, TOKEN_LT, TOKEN_IS):
            token = self.current_token
            self.eat(token.type)
            if token.type == TOKEN_IS:
                target = self.bitwise_expr()
                node = TypeCheckOp(node, target)
            else:
                node = BinaryOp(left=node, op=token, right=self.bitwise_expr())
        return node

    def arithmetic_expr(self):
        node = self.term()
        while self.current_token.type in (TOKEN_PLUS, TOKEN_MINUS, TOKEN_EQ, TOKEN_NEQ, TOKEN_GT, TOKEN_LT):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.term())
        return node

    def logic_expr(self):
        node = self.comp_expr()
        while self.current_token.type in (TOKEN_AND, TOKEN_OR):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.comp_expr())
        return node

    def expr(self):
        node = self.logic_expr()
        
        if self.current_token.type == TOKEN_QUESTION:
            self.eat(TOKEN_QUESTION)
            true_expr = self.expr()
            self.eat(TOKEN_COLON)
            false_expr = self.expr()
            return TernaryOp(node, true_expr, false_expr)
        
        return node

    def parse_statement(self):
        # Capture line number of the start of the statement
        start_line = self.current_token.line
        node = self._parse_statement_body()
        
        # Attach line number to the AST node
        if isinstance(node, AST):
            node.line = start_line
        return node

    def _parse_statement_body(self):
        token = self.current_token
        
        if token.type == TOKEN_KEYWORD and token.value == 'import':
            self.eat(TOKEN_KEYWORD)
            if self.current_token.type == TOKEN_ID:
                name = self.current_token.value
                self.eat(TOKEN_ID)
                return ImportStatement(name)
            elif self.current_token.type == TOKEN_STRING:
                name = self.current_token.value
                self.eat(TOKEN_STRING)
                return ImportStatement(name)
            else:
                raise Exception("Syntax Error: Expected module name after 'import'")
            
        elif token.type == TOKEN_KEYWORD and token.value == 'import_py':
            self.eat(TOKEN_KEYWORD)
            name = ""
            if self.current_token.type == TOKEN_ID:
                name = self.current_token.value
                self.eat(TOKEN_ID)
            elif self.current_token.type == TOKEN_STRING:
                name = self.current_token.value
                self.eat(TOKEN_STRING)
            else:
                raise Exception("Syntax Error: Expected Python module name after 'import_py'")
            
            return ImportPyStatement(name, alias=name)

        elif token.type == TOKEN_KEYWORD and (token.value == 'let' or token.value == 'const'):
            is_const = (token.value == 'const')
            self.eat(TOKEN_KEYWORD)
            
            if not is_const and self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'const':
                self.eat(TOKEN_KEYWORD)
                is_const = True

            if self.current_token.type == TOKEN_LBRACKET:
                self.eat(TOKEN_LBRACKET)
                names = []
                names.append(self.current_token.value)
                self.eat(TOKEN_ID)
                
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    names.append(self.current_token.value)
                    self.eat(TOKEN_ID)
                
                self.eat(TOKEN_RBRACKET)
                self.eat(TOKEN_ASSIGN)
                val = self.expr()
                return DestructuringDecl(names, val, is_const)

            var_name = self.current_token.value
            self.eat(TOKEN_ID)
            self.eat(TOKEN_ASSIGN)
            val = self.expr()
            return VarDecl(var_name, val, is_const)
        
        elif token.type == TOKEN_KEYWORD and token.value == 'func':
            self.eat(TOKEN_KEYWORD)
            func_name = self.current_token.value
            self.eat(TOKEN_ID)
            self.eat(TOKEN_LPAREN)
            
            params = []
            if self.current_token.type != TOKEN_RPAREN:
                # 1st Param
                p_name = self.current_token.value
                self.eat(TOKEN_ID)
                p_def = None
                if self.current_token.type == TOKEN_ASSIGN:
                    self.eat(TOKEN_ASSIGN)
                    p_def = self.expr()
                params.append((p_name, p_def))
                
                # Rest
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    p_name = self.current_token.value
                    self.eat(TOKEN_ID)
                    p_def = None
                    if self.current_token.type == TOKEN_ASSIGN:
                        self.eat(TOKEN_ASSIGN)
                        p_def = self.expr()
                    params.append((p_name, p_def))
            
            self.eat(TOKEN_RPAREN)
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            return FunctionDef(func_name, params, body)

        elif token.type == TOKEN_KEYWORD and token.value == 'class':
            self.eat(TOKEN_KEYWORD)
            class_name = self.current_token.value
            self.eat(TOKEN_ID)
            
            superclass = None
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'extends':
                self.eat(TOKEN_KEYWORD)
                superclass = self.current_token.value
                self.eat(TOKEN_ID)
            
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            
            return ClassDef(class_name, body, superclass)

        elif token.type == TOKEN_KEYWORD and token.value == 'return':
            self.eat(TOKEN_KEYWORD)
            val = self.expr()
            return ReturnStatement(val)

        elif token.type == TOKEN_KEYWORD and token.value == 'if':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            cond = self.expr()
            self.eat(TOKEN_RPAREN)
            self.eat(TOKEN_LBRACE)
            true_block = self.block()
            self.eat(TOKEN_RBRACE)
            false_block = None
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'else':
                self.eat(TOKEN_KEYWORD)
                self.eat(TOKEN_LBRACE)
                false_block = self.block()
                self.eat(TOKEN_RBRACE)
            return IfStatement(cond, true_block, false_block)

        elif token.type == TOKEN_KEYWORD and token.value == 'while':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            cond = self.expr()
            self.eat(TOKEN_RPAREN)
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            return WhileStatement(cond, body)

        elif token.type == TOKEN_KEYWORD and token.value == 'for':
            self.eat(TOKEN_KEYWORD)
            iter_name = self.current_token.value
            self.eat(TOKEN_ID)
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'in':
                self.eat(TOKEN_KEYWORD)
            else:
                raise Exception("Syntax Error: Expected 'in' after for loop's variable")
            iterable = self.expr()
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            return ForStatement(iter_name, iterable, body)

        elif token.type == TOKEN_KEYWORD and token.value == 'attempt':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LBRACE)
            try_block = self.block()
            self.eat(TOKEN_RBRACE)
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'rescue':
                self.eat(TOKEN_KEYWORD)
                self.eat(TOKEN_LPAREN)
                error_var = self.current_token.value
                self.eat(TOKEN_ID)
                self.eat(TOKEN_RPAREN)
                self.eat(TOKEN_LBRACE)
                catch_block = self.block()
                self.eat(TOKEN_RBRACE)
                return TryCatchStatement(try_block, error_var, catch_block)
            else:
                raise Exception("Syntax Error: No 'rescue' block found after 'attempt'")
            
        elif token.type == TOKEN_KEYWORD and token.value == 'enum':
            self.eat(TOKEN_KEYWORD)
            name = self.current_token.value
            self.eat(TOKEN_ID)
            self.eat(TOKEN_LBRACE)
            
            members = []
            if self.current_token.type != TOKEN_RBRACE:
                members.append(self.current_token.value)
                self.eat(TOKEN_ID)
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    members.append(self.current_token.value)
                    self.eat(TOKEN_ID)
            
            self.eat(TOKEN_RBRACE)
            return EnumDef(name, members)

        elif token.type == TOKEN_KEYWORD and token.value == 'break':
            self.eat(TOKEN_KEYWORD)
            return BreakStatement()

        elif token.type == TOKEN_KEYWORD and token.value == 'advance':
            self.eat(TOKEN_KEYWORD)
            return AdvanceStatement()

        elif token.type == TOKEN_KEYWORD and token.value == 'leap':
            self.eat(TOKEN_KEYWORD)
            if self.current_token.type == TOKEN_ID:
                target = Identifier(self.current_token)
                self.eat(TOKEN_ID)
                return LeapStatement(target)
            elif self.current_token.type == TOKEN_INT:
                target = Number(self.current_token)
                self.eat(TOKEN_INT)
                return LeapStatement(target)
            else:
                raise Exception("Syntax Error: Leap target must be a label name or line number")
    
        elif token.type == TOKEN_LBRACE:
            if (self.pos + 1 < len(self.tokens) and 
                self.tokens[self.pos+1].type == TOKEN_ID and 
                self.pos + 2 < len(self.tokens) and 
                self.tokens[self.pos+2].type == TOKEN_RBRACE):
                
                self.eat(TOKEN_LBRACE)
                name = self.current_token.value
                self.eat(TOKEN_ID)
                self.eat(TOKEN_RBRACE)
                return LabelDef(name)
            
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            return body

        elif token.type == TOKEN_KEYWORD and token.value == 'match':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            subject = self.expr()
            self.eat(TOKEN_RPAREN)
            self.eat(TOKEN_LBRACE)
            
            cases = []
            default_block = None
            
            while self.current_token.type != TOKEN_RBRACE and self.current_token.type != TOKEN_EOF:
                
                if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'other':
                    self.eat(TOKEN_KEYWORD)
                    self.eat(TOKEN_COLON)
                    
                    stmts = []
                    while self.current_token.type != TOKEN_RBRACE and self.current_token.type != TOKEN_EOF:
                         stmts.append(self.parse_statement())
                    
                    default_block = Block(stmts)
                
                else:
                    val = self.expr()
                    self.eat(TOKEN_COLON)
                    
                    stmts = []
                    while (self.current_token.type != TOKEN_RBRACE and 
                           self.current_token.type != TOKEN_EOF and 
                           not self.is_case_start() and 
                           not (self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'other')):
                        
                        stmts.append(self.parse_statement())
                    
                    cases.append(MatchCase(val, Block(stmts)))

            self.eat(TOKEN_RBRACE)
            return MatchStatement(subject, cases, default_block)

        else:
            expr_node = self.expr()
            
            # Normal Assign
            if self.current_token.type == TOKEN_ASSIGN:
                self.eat(TOKEN_ASSIGN)
                val = self.expr()
                return Assign(expr_node, val)
            
            # Compound Assign
            elif self.current_token.type in (TOKEN_PLUSEQ, TOKEN_MINUSEQ, TOKEN_MULEQ, TOKEN_DIVEQ):
                op = self.current_token
                self.eat(op.type)
                val = self.expr()
                return CompoundAssign(expr_node, op, val)
                
            return expr_node
    
    def block(self):
        statements = []
        while self.current_token.type != TOKEN_RBRACE and self.current_token.type != TOKEN_EOF:
            statements.append(self.parse_statement())
        return Block(statements)

    def parse(self):
        statements = []
        while self.current_token.type != TOKEN_EOF:
            statements.append(self.parse_statement())
        return Block(statements)

# ==========================================
# INTERPRETER & ENVIRONMENT
# ==========================================

class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.constants = set()
        self.parent = parent

    def get(self, name):
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        raise Exception(f"Runtime Error: Variable '{name}' is undefined")

    def define(self, name, value, is_const=False):
        self.values[name] = value
        if is_const:
            self.constants.add(name)

    def assign(self, name, value):
        if name in self.values:
            if name in self.constants:
                raise Exception(f"Runtime Error: Cannot reassign constant '{name}'")
            self.values[name] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise Exception(f"Runtime Error: Undefined variable '{name}' cannot be assigned a value")
    
class LuniteInstance:
    def __init__(self, mold_node):
        self.mold = mold_node
        self.fields = {}
        self.methods = {}
    
    def get(self, name):
        if name in self.fields:
            return self.fields[name]
        if name in self.methods:
            return self.methods[name]
        raise Exception(f"Runtime Error: Class '{self.mold.name}' does not contain the property '{name}'")

    def set(self, name, val):
        self.fields[name] = val

    def __repr__(self):
        return f"<Instance of {self.mold.name}>"

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class BreakException(Exception): pass

class AdvanceException(Exception): pass

class LeapException(Exception): 
    def __init__(self, target):
        self.target = target

class Interpreter:
    def __init__(self, imported_files=None):
        self.global_env = Environment()
        self.setup_std_lib()
        self.env = self.global_env
        self.imported_files = imported_files if imported_files else set()

    def setup_std_lib(self):
        def clean_str(val):
            if isinstance(val, bool): return "true" if val else "false"
            if isinstance(val, float): return f"{val:.12g}"
            if val is None: return "null"
            if isinstance(val, (bytes, bytearray)): return f"<Bytes len={len(val)}>"
            if isinstance(val, (set, tuple)): return str(val)
            return str(val)

        # --- IO (Enhanced) ---
        self.global_env.define('out', lambda x: print(clean_str(x)))
        
        def lunite_input(prompt, type_hint="string"):
            text = input(clean_str(prompt))
            
            try:
                if type_hint == "int": return int(text)
                if type_hint == "float": return float(text)
                if type_hint == "bool": return text.lower() in ("true", "1", "yes", "on")
                if type_hint == "bit": return LBit(text)
                if type_hint == "byte": return LByte(text)
                if type_hint == "char": return LChar(text)
                return text
            except ValueError:
                raise Exception(f"Input Error: Failed to convert '{text}' to type {type_hint}")
                
        self.global_env.define('in', lunite_input)
        
        # --- File IO ---
        def read_file(path):
            try:
                with open(path, 'r') as f: return f.read()
            except Exception as e: raise Exception(str(e))
        
        def write_file(path, content):
            try:
                with open(path, 'w') as f: f.write(clean_str(content))
            except Exception as e: raise Exception(str(e))
        
        self.global_env.define('read_file', read_file)
        self.global_env.define('write_file', write_file)

        # --- File System & Path ---
        self.global_env.define('mkdir', lambda p: os.mkdir(str(p)))
        self.global_env.define('rmdir', lambda p: os.rmdir(str(p)))
        self.global_env.define('remove', lambda p: os.remove(str(p)))
        self.global_env.define('listdir', lambda p: os.listdir(str(p)))
        self.global_env.define('exists', lambda p: os.path.exists(str(p)))
        self.global_env.define('path_join', lambda a, b: os.path.join(str(a), str(b)))
        self.global_env.define('getcwd', lambda: os.getcwd())

        # --- System ---
        def stop_impl(code=0):
            sys.stdout.flush()
            
            exit_code = 0
            try:
                exit_code = int(code)
            except (ValueError, TypeError):
                exit_code = 0
            
            sys.exit(exit_code)

        self.global_env.define('cmd', lambda c: subprocess.getoutput(c))
        self.global_env.define('os_name', lambda: platform.system())
        self.global_env.define('stop', stop_impl)
        self.global_env.define('args', lambda: sys.argv)
        self.global_env.define('env', lambda key: os.environ.get(str(key), None))
        
        # --- Network ---
        def http_get(url):
            try:
                with urllib.request.urlopen(url) as response:
                   return response.read().decode('utf-8')
            except Exception as e:
                raise Exception(str(e))
        
        def http_post(url, data):
            try:
                if isinstance(data, (dict, list)):
                    payload = json.dumps(data).encode('utf-8')
                    headers = {'Content-Type': 'application/json', 'User-Agent': LUNITE_USER_AGENT}
                else:
                    payload = clean_str(data).encode('utf-8')
                    headers = {'User-Agent': LUNITE_USER_AGENT}
                
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                with urllib.request.urlopen(req) as response:
                    return response.read().decode('utf-8')
            except Exception as e:
                raise Exception(str(e))

        self.global_env.define('http_get', http_get)
        self.global_env.define('http_post', http_post)
        self.global_env.define('json_encode', lambda x: json.dumps(x))
        self.global_env.define('json_decode', lambda x: json.loads(x))

        # --- Binary (Bytes) I/O ---
        def read_bytes(path):
            try:
                with open(path, 'rb') as f: return f.read()
            except Exception as e: return None
        
        def write_bytes(path, data):
            try:
                if isinstance(data, str): data = data.encode('utf-8')
                with open(path, 'wb') as f: f.write(data)
            except Exception as e: raise Exception(str(e))

        self.global_env.define('read_bytes', read_bytes)
        self.global_env.define('write_bytes', write_bytes)
        self.global_env.define('bytes', lambda lst: bytes(lst))

        # --- Regex ---
        class RegexWrapper:
            def match(self, pattern, string):
                return bool(re.match(pattern, string))
            
            def search(self, pattern, string):
                m = re.search(pattern, string)
                if m: return m.groups()
                return None
            
            def find_all(self, pattern, string):
                return re.findall(pattern, string)
            
            def replace(self, pattern, repl, string):
                return re.sub(pattern, repl, string)

        regex_obj = LuniteInstance(ClassDef("Regex", Block([]), None))
        regex_wrapper = RegexWrapper()
        regex_obj.methods['match'] = lambda p, s: regex_wrapper.match(p, s)
        regex_obj.methods['search'] = lambda p, s: regex_wrapper.search(p, s)
        regex_obj.methods['find_all'] = lambda p, s: regex_wrapper.find_all(p, s)
        regex_obj.methods['replace'] = lambda p, r, s: regex_wrapper.replace(p, r, s)
        
        self.global_env.define('Regex', regex_obj)

        # --- Math ---
        self.global_env.define('sin', lambda x: math.sin(x))
        self.global_env.define('cos', lambda x: math.cos(x))
        self.global_env.define('tan', lambda x: math.tan(x))
        self.global_env.define('sqrt', lambda x: math.sqrt(x))
        self.global_env.define('pow', lambda x, y: math.pow(x, y))
        self.global_env.define('abs', lambda x: abs(x))
        self.global_env.define('round', lambda x: round(x))
        self.global_env.define('floor', lambda x: math.floor(x))
        self.global_env.define('ceil', lambda x: math.ceil(x))
        self.global_env.define('random', lambda: random.random())
        self.global_env.define('randint', lambda a, b: random.randint(a, b))
        self.global_env.define('range', lambda a, b: list(range(a, b)))

        # --- Time & Date Helper ---
        def date_struct_impl(ts=None):
            if ts is None: ts = time.time()
            dt = datetime.datetime.fromtimestamp(ts)
            return {
                "year": dt.year, "month": dt.month, "day": dt.day,
                "hour": dt.hour, "minute": dt.minute, "second": dt.second,
                "weekday": dt.weekday()
            }
        self.global_env.define('date_struct', date_struct_impl)
        self.global_env.define('wait', lambda x: time.sleep(x))
        self.global_env.define('time', lambda: time.time())

        # --- Data ---
        self.global_env.define('str', lambda x: clean_str(x))
        self.global_env.define('int', lambda x: int(x))
        self.global_env.define('float', lambda x: float(x))
        self.global_env.define('bit', lambda x: LBit(x))
        self.global_env.define('byte', lambda x: LByte(x))
        self.global_env.define('char', lambda x: LChar(str(x)) if isinstance(x, (int, float)) else LChar(x))

        # --- String / Utils ---
        def get_type(x):
            if isinstance(x, LBit): return "Bit"
            if isinstance(x, LByte): return "Byte"
            if isinstance(x, LChar): return "Char"
            if isinstance(x, bool): return "Bool"
            if isinstance(x, int): return "Int"
            if isinstance(x, float): return "Float"
            if isinstance(x, str): return "String"
            if isinstance(x, list): return "List"
            if isinstance(x, dict): return "Dict"
            if isinstance(x, set): return "Set"
            if isinstance(x, tuple): return "Tuple"
            if isinstance(x, LuniteInstance): return x.mold.name
            if x is None: return "Null"
            if type(x).__name__ == 'module': return "PyModule"
            return "Unknown"
    
        self.global_env.define('len', lambda x: len(x))
        self.global_env.define('type', get_type)
        
        self.global_env.define('to_upper', lambda x: clean_str(x).upper())
        self.global_env.define('to_lower', lambda x: clean_str(x).lower())
        self.global_env.define('trim', lambda x: clean_str(x).strip())
        self.global_env.define('replace', lambda s, old, new: clean_str(s).replace(clean_str(old), clean_str(new)))
        self.global_env.define('split', lambda s, d: clean_str(s).split(clean_str(d)))
        self.global_env.define('join', lambda lst, d: clean_str(d).join([clean_str(i) for i in lst]))
        
        self.global_env.define('raise', lambda msg: (_ for _ in ()).throw(Exception(msg)))
    
    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        method = getattr(self, method_name, self.no_visit)
        return method(node)

    def no_visit(self, node):
        raise Exception(f"Internal Lunite Error: No visit_{type(node).__name__} method defined")

    def visit_Block(self, node):
        result = None
        statements = node.statements
        i = 0
        while i < len(statements):
            stmt = statements[i]
            try:
                result = self.visit(stmt)
                i += 1
            except LeapException as e:
                target = e.target
                found = False
                
                for idx, s in enumerate(statements):
                    if isinstance(target, str): 
                        if isinstance(s, LabelDef) and s.name == target:
                            i = idx
                            found = True
                            break
                    elif isinstance(target, int):
                        if s.line == target:
                            i = idx
                            found = True
                            break
                
                if found:
                    continue
                else:
                    raise e
        return result
    
    def visit_Number(self, node):
        return node.token.value

    def visit_String(self, node):
        return node.token.value
    
    def visit_Char(self, node):
        return LChar(node.token.value)

    def visit_Boolean(self, node):
        return node.value

    def visit_Null(self, node):
        return None

    def visit_ListLiteral(self, node):
        return [self.visit(e) for e in node.elements]

    def visit_DictLiteral(self, node):
        return {self.visit(k): self.visit(v) for k, v in node.pairs}

    def visit_Identifier(self, node):
        return self.env.get(node.token.value)

    def visit_MatchCase(self, node):
        return self.visit(node.value)

    def visit_MatchStatement(self, node):
        subject_val = self.visit(node.subject)
        matched = False
        
        try:
            for case in node.cases:
                case_val = self.visit_MatchCase(case)
                
                if subject_val == case_val:
                    self.visit(case.body)
                    matched = True
                    break
            
            if not matched and node.default_block:
                self.visit(node.default_block)

        except BreakException:
            pass
    
    def visit_UnaryOp(self, node):
        op = node.op.type
        val = self.visit(node.expr)
        
        if op == TOKEN_MINUS: return -val
        if op == TOKEN_PLUS: return +val
        if op == TOKEN_BIT_NOT: return ~val
        if op == TOKEN_NOT: return not val
        return val
    
    def visit_BinaryOp(self, node):
        op = node.op.type

        if op == TOKEN_AND:
            left = self.visit(node.left)
            if not left: return False
            return self.visit(node.right)
            
        if op == TOKEN_OR:
            left = self.visit(node.left)
            if left: return True
            return self.visit(node.right)

        left = self.visit(node.left)
        right = self.visit(node.right)

        # Math
        if op == TOKEN_PLUS: return left + right
        if op == TOKEN_MINUS: return left - right
        if op == TOKEN_MUL: return left * right
        if op == TOKEN_DIV: return left / right
        
        # Bitwise
        if op == TOKEN_BIT_AND: return left & right
        if op == TOKEN_BIT_OR:  return left | right
        if op == TOKEN_BIT_XOR: return left ^ right
        if op == TOKEN_LSHIFT:  return left << right
        if op == TOKEN_RSHIFT:  return left >> right
        
        # Comparison
        if op == TOKEN_GT: return left > right
        if op == TOKEN_LT: return left < right
        if op == TOKEN_EQ: return left == right
        if op == TOKEN_NEQ: return left != right
        
        return None
    
    def visit_TernaryOp(self, node):
        if self.visit(node.condition):
            return self.visit(node.true_expr)
        else:
            return self.visit(node.false_expr)

    def visit_VarDecl(self, node):
        val = self.visit(node.value)
        self.env.define(node.name, val, is_const=node.is_const)
        return val

    def visit_Assign(self, node):
        val = self.visit(node.value)
        
        if isinstance(node.left, Identifier):
            self.env.assign(node.left.token.value, val)
        
        elif isinstance(node.left, MemberAccess):
            obj = self.visit(node.left.obj)
            if isinstance(obj, LuniteInstance):
                obj.set(node.left.member_name, val)
            else:
                raise Exception("Assignment Error: Cannot set a property on a non-instance")
        
        elif isinstance(node.left, IndexAccess):
            target = self.visit(node.left.target)
            index = self.visit(node.left.index)
            try:
                target[index] = val
            except TypeError:
                raise Exception("Assignment Error: Target does not support index assignment")
            except IndexError:
                raise Exception("Assignment Error: Provided index is out of bounds")
        else:
            raise Exception("Assignment Error: No such assignment target")

        return val

    def visit_CompoundAssign(self, node):
        curr_val = 0
        if isinstance(node.left, Identifier):
            curr_val = self.env.get(node.left.token.value)
        elif isinstance(node.left, MemberAccess):
            obj = self.visit(node.left.obj)
            curr_val = obj.get(node.left.member_name)
        elif isinstance(node.left, IndexAccess):
            target = self.visit(node.left.target)
            index = self.visit(node.left.index)
            curr_val = target[index]
        else:
            raise Exception("Invalid target for compound assignment")

        right_val = self.visit(node.value)
        op = node.op.type
        new_val = curr_val
        
        if op == TOKEN_PLUSEQ: new_val += right_val
        if op == TOKEN_MINUSEQ: new_val -= right_val
        if op == TOKEN_MULEQ: new_val *= right_val
        if op == TOKEN_DIVEQ: new_val /= right_val

        if isinstance(node.left, Identifier):
            self.env.assign(node.left.token.value, new_val)
        elif isinstance(node.left, MemberAccess):
            obj.set(node.left.member_name, new_val)
        elif isinstance(node.left, IndexAccess):
            target[self.visit(node.left.index)] = new_val
            
        return new_val

    def visit_BinaryOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op.type

        if op == TOKEN_PLUS: return left + right
        if op == TOKEN_MINUS: return left - right
        if op == TOKEN_MUL: return left * right
        if op == TOKEN_DIV: return left / right
        if op == TOKEN_GT: return left > right
        if op == TOKEN_LT: return left < right
        if op == TOKEN_EQ: return left == right
        if op == TOKEN_NEQ: return left != right
        return None

    def visit_IfStatement(self, node):
        if self.visit(node.condition):
            return self.visit(node.true_block)
        elif node.false_block:
            return self.visit(node.false_block)

    def visit_WhileStatement(self, node):
        while self.visit(node.condition):
            try:
                self.visit(node.body)
            except BreakException:
                break
            except AdvanceException:
                continue
    
    def visit_ForStatement(self, node):
        iterable = self.visit(node.iterable)
        if not hasattr(iterable, '__iter__'):
             raise Exception("Loop Error: For loop expects an iterable, but none were provided")

        prev_env = self.env
        for item in iterable:
            loop_env = Environment(prev_env)
            loop_env.define(node.iterator_name, item)
            self.env = loop_env
            try:
                self.visit(node.body)
            except ReturnException as e:
                self.env = prev_env
                raise e 
            except BreakException:
                self.env = prev_env
                break
            except AdvanceException:
                self.env = prev_env
                continue
        self.env = prev_env

    def visit_BreakStatement(self, node):
        raise BreakException()

    def visit_AdvanceStatement(self, node):
        raise AdvanceException()

    def visit_LeapStatement(self, node):
        if isinstance(node.target, Identifier):
            raise LeapException(node.target.token.value)
        elif isinstance(node.target, Number):
            raise LeapException(node.target.token.value)

    def visit_LabelDef(self, node):
        pass

    def visit_TryCatchStatement(self, node):
        try:
            return self.visit(node.try_block)
        except Exception as e:
            if isinstance(e, ReturnException):
                raise e
            
            prev_env = self.env
            rescue_env = Environment(prev_env)
            rescue_env.define(node.error_var, str(e))
            self.env = rescue_env
            
            try:
                return self.visit(node.catch_block)
            finally:
                self.env = prev_env

    def visit_ImportStatement(self, node):
        fname = node.module_name
        if not fname.endswith('.luna'):
            fname += '.luna'
        
        if fname in self.imported_files:
            return 
        
        if not os.path.exists(fname):
             raise Exception(f"Import Error: Module '{fname}' not found or does not exist")
        
        with open(fname, 'r') as f:
            code = f.read()
        
        self.imported_files.add(fname)
        
        lexer = Lexer(code)
        tokens = []
        while True:
            t = lexer.get_next_token()
            tokens.append(t)
            if t.type == TOKEN_EOF: break
        
        parser = Parser(tokens)
        ast = parser.parse()
        self.visit(ast)

    def visit_FunctionDef(self, node):
        self.env.define(node.name, node)
        return node

    def visit_ClassDef(self, node):
        self.env.define(node.name, node)
        return node

    def visit_ReturnStatement(self, node):
        val = self.visit(node.value)
        raise ReturnException(val)

    def visit_FunctionCall(self, node):
        func = self.env.get(node.name)
        if callable(func): # Std Lib
            try:
                args = [self.visit(arg) for arg in node.args]
                return func(*args)
            except Exception as e:
                raise Exception(str(e))
        
        if isinstance(func, (FunctionDef, LambdaExpr)):
            prev_env = self.env
            new_env = Environment(self.global_env)
            f_params = func.params
            
            if isinstance(func, LambdaExpr):
                f_params = [(p, None) for p in f_params]

            if len(node.args) > len(f_params):
                raise Exception(f"Function Error: Too many arguments.")

            for i, (p_name, p_default) in enumerate(f_params):
                if i < len(node.args):
                    # Value provided
                    val = self.visit(node.args[i])
                    new_env.define(p_name, val)
                elif p_default is not None:
                    # Use Default
                    val = self.visit(p_default)
                    new_env.define(p_name, val)
                else:
                    raise Exception(f"Function Error: Missing argument for '{p_name}'")
            
            self.env = new_env
            try:
                if isinstance(func.body, Block):
                    self.visit(func.body)
                else:
                    return self.visit(func.body)
            except ReturnException as e:
                self.env = prev_env
                return e.value
            self.env = prev_env
            return None
        
        raise Exception(f"Function Error: '{node.name}' is not a function")

    def visit_LambdaExpr(self, node):
        return node
    
    def visit_TypeCheckOp(self, node):
        val = self.visit(node.expr)
        
        target = node.target
        type_name = ""
        
        if isinstance(target, Identifier):
            type_name = target.token.value
        
        # Primitive Checks
        if type_name == 'int': return isinstance(val, int) and not isinstance(val, bool)
        if type_name == 'float': return isinstance(val, float)
        if type_name == 'str': return isinstance(val, str) and not isinstance(val, LChar)
        if type_name == 'bool': return isinstance(val, bool)
        if type_name == 'list': return isinstance(val, list)
        if type_name == 'dict': return isinstance(val, dict)
        if type_name == 'char': return isinstance(val, LChar)
        if type_name == 'bit': return isinstance(val, LBit)
        if type_name == 'byte': return isinstance(val, LByte)
        
        if isinstance(val, LuniteInstance):
            if isinstance(target, Identifier):
                return val.mold.name == type_name
                # TODO: Check inheritance tree for 'is'
                
        return False

    def _resolve_class_members(self, class_def):
        members = {'fields': {}, 'methods': {}}
        
        if class_def.superclass:
            super_node = self.env.get(class_def.superclass)
            if isinstance(super_node, ClassDef):
                super_members = self._resolve_class_members(super_node)
                members['fields'].update(super_members['fields'])
                members['methods'].update(super_members['methods'])
            else:
                raise Exception(f"Class Error: Superclass {class_def.superclass} is not a valid class")

        prev_env = self.env
        class_env = Environment(self.global_env)
        self.env = class_env
        
        for stmt in class_def.body.statements:
            if isinstance(stmt, FunctionDef):
                members['methods'][stmt.name] = stmt
            elif isinstance(stmt, VarDecl):
                self.visit(stmt)
                members['fields'][stmt.name] = class_env.values[stmt.name]
            else:
                self.visit(stmt)

        self.env = prev_env
        return members
    
    def visit_NewInstance(self, node):
        cls_def = self.env.get(node.class_name)
        if not isinstance(cls_def, ClassDef):
            raise Exception(f"Class Error: {node.class_name} is not a class")
        
        instance = LuniteInstance(cls_def)
        
        # Populate instance with all inherited members
        members = self._resolve_class_members(cls_def)
        instance.fields = members['fields']
        instance.methods = members['methods']
        
        # 3. Call Constructor if it exists
        if 'init' in instance.methods:
            init_method = instance.methods['init']
            
            # Setup context for init call
            prev_env = self.env
            method_env = Environment(self.global_env)
            method_env.define('this', instance)
            
            # Arg matching
            if len(node.args) != len(init_method.params):
                raise Exception(f"Class Error: Constructor expects {len(init_method.params)} args, got {len(node.args)}")

            for name, arg_node in zip(init_method.params, node.args):
                method_env.define(name, self.visit(arg_node))

            self.env = method_env
            try:
                self.visit(init_method.body)
            except ReturnException:
                pass # Constructors return nothing
            finally:
                self.env = prev_env
                
        return instance

    def visit_MethodCall(self, node):
        obj = self.visit(node.obj)
        if not isinstance(obj, LuniteInstance):
            raise Exception("Method Error: Method call on non-instance")

        method = obj.methods.get(node.method_name)
        if not method:
             field = obj.fields.get(node.method_name)
             if field and callable(field):
                 raise Exception(f"Method Error: Property '{node.method_name}' is not a method (Lambdas not fully supported yet)")
             raise Exception(f"Method Error: Method '{node.method_name}' not found on instance")

        prev_env = self.env
        method_env = Environment(self.global_env)
        method_env.define('this', obj)
        
        for name, arg_node in zip(method.params, node.args):
            method_env.define(name, self.visit(arg_node))

        self.env = method_env
        try:
            self.visit(method.body)
        except ReturnException as e:
            self.env = prev_env
            return e.value
        self.env = prev_env
        return None
    
    def visit_MemberAccess(self, node):
        obj = self.visit(node.obj)
        if isinstance(obj, LuniteInstance):
            return obj.get(node.member_name)
        raise Exception("Member Error: Member access on non-instance")

    def visit_IndexAccess(self, node):
        target = self.visit(node.target)
        index = self.visit(node.index)
        try:
            return target[index]
        except Exception:
            raise Exception("Index Error: Index out of bounds or invalid target")
        
    def visit_ImportPyStatement(self, node):
        try:
            mod = importlib.import_module(node.module_name)
            self.env.define(node.alias, mod)
        except ImportError:
            raise Exception(f"Runtime Error: Python module '{node.module_name}' not found")

    def visit_SetLiteral(self, node):
        elements = [self.visit(e) for e in node.elements]
        return set(elements)

    def visit_TupleLiteral(self, node):
        elements = [self.visit(e) for e in node.elements]
        return tuple(elements)
    
    def visit_EnumDef(self, node):
        enum_val = LuniteInstance(ClassDef(node.name, Block([]), None))
        for i, member in enumerate(node.members):
            enum_val.fields[member] = i
        self.env.define(node.name, enum_val, is_const=True)
        return enum_val
    
    def visit_DestructuringDecl(self, node):
        val = self.visit(node.value)
        if not hasattr(val, '__getitem__') or not hasattr(val, '__len__'):
             raise Exception("Destructuring Error: Value is not iterable (must be List, Tuple, or String)")
        if len(val) < len(node.names):
             raise Exception(f"Destructuring Error: Not enough values to unpack (expected {len(node.names)}, got {len(val)})")
        for i, name in enumerate(node.names):
            self.env.define(name, val[i], is_const=node.is_const)
        return val

# ==========================================
# CLI & BUILDER
# ==========================================

def start_repl():
    print(f"Lunite {LUNITE_VERSION_STR} REPL CLI")
    print(f"{COPYRIGHT}")
    print("Run Lunite code line-by-line.")
    print("Type 'exit' or 'quit' to quit.")
    print("-" * 30)

    interpreter = Interpreter()
    
    while True:
        try:
            text = input("lunite> ")
            if text.strip() == "": continue
            if text.strip() in ["exit", "quit"]: break
            
            lexer = Lexer(text)
            tokens = []
            while True:
                tok = lexer.get_next_token()
                tokens.append(tok)
                if tok.type == TOKEN_EOF: break
            
            parser = Parser(tokens)
            ast = parser.parse() 
            
            if isinstance(ast, Block):
                for stmt in ast.statements:
                    res = interpreter.visit(stmt)
                    if res is not None:
                        print(interpreter.global_env.values.get('str')(res))
            
        except Exception as e:
            print(f"Error: {e}")

def run_code(source):
    lexer = Lexer(source)
    tokens = []
    while True:
        tok = lexer.get_next_token()
        tokens.append(tok)
        if tok.type == TOKEN_EOF:
            break
    
    parser = Parser(tokens)
    try:
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.visit(ast)
    except LeapException as e:
        print(f"Runtime Error: Jump target '{e.target}' not found (or jump out of scope).")
    except BreakException:
        print("Runtime Error: 'break' outside of loop.")
    except AdvanceException:
        print("Runtime Error: 'advance' outside of loop.")
    except ReturnException:
        print("Runtime Error: 'return' outside of function.")
    except Exception as e:
        print(f"Lunite Error: {e}")

# [RUNTIME BINDED CODE END]

def compile_code(filename):
    with open(filename, 'r') as f:
        print(f"Build: Opened source '{filename}' to read.")
        source = f.read()
        print(f"Build: Read source file.")
    
    this_file = os.path.abspath(__file__)
    with open(this_file, 'r') as f:
        print(f"Build: Reading Lunite engine source: {this_file}")
        engine_code = f.read()
        print(f"Build: Read Lunite engine source.")

    print(f"Build: Sanitizing Lunite...")
    engine_code = engine_code.split("# [RUNTIME BINDED CODE END]")[0]
    print(f"Build: Lunite has been cleaned.")

    print(f"Build: Creating proper loader code...")
    loader_code = f"""
{engine_code}

if __name__ == "__main__":
    source_code = {json.dumps(source)}
    run_code(source_code)
"""
    print(f"Build: Created proper loader code.")

    dist_file = filename.replace('.luna', '.py')
    with open(dist_file, 'w') as f:
        print(f"Build: Writing loader code to '{dist_file}'")
        f.write(loader_code)
    
    print(f"Build: Created intermediate {dist_file}")
    print("Build: Compiling with PyInstaller, this might take some time...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "--onefile", dist_file])
        print(f"Build: Success! Executable should be in the 'dist' folder.")
    except Exception as e:
        print(f"Build: Compilation failed: {e}")
    finally:
        if os.path.exists(dist_file):
            os.remove(dist_file)
        if os.path.exists(filename.replace('.luna', '.spec')):
            os.remove(filename.replace('.luna', '.spec'))

def clean_build():
    try:
        print("Clean: Cleaning build directories...")
        shutil.rmtree("./build", ignore_errors=False)
        shutil.rmtree("./dist", ignore_errors=False)
        print("Clean: Cleanup successful.")
    except Exception as e:
        print(f"Clean error: {e}")

def main():
    if len(sys.argv) < 2:
        start_repl()
        return

    command = sys.argv[1]
    
    if command == 'run':
        if len(sys.argv) < 3:
            print("The Lunite Programming Language")
            print(LUNITE_VERSION_STR)
            print(COPYRIGHT)
            print("-------------------------------")
            print("Run failed: File not provided.")
            return
        path = sys.argv[2]
        if os.path.exists(path):
            with open(path, 'r') as f:
                run_code(f.read())
        else:
            print("The Lunite Programming Language")
            print(LUNITE_VERSION_STR)
            print(COPYRIGHT)
            print("-------------------------------")
            print("Run failed: File not found.")

    elif command == 'build':
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
        print("-------------------------------")
        print("WARNING: Building is a WIP feature, might not work as intended.")
        print("         Executable will be placed in './dist' after build by PyInstaller.")
        print("         Building can overwrite files in './build' and './dist'.")
        cnt_build = input("Continue with build? [Y/N]: ")
        if cnt_build.lower().startswith('y'):
            if len(sys.argv) < 3:
                print("Build failed: File not provided.")
                return
            print("-------------------------------")
            compile_code(sys.argv[2])
        elif cnt_build.lower().startswith('n'):
            print("Build failed: Aborted by user.")
            return
        else:
            print("Build failed: Unknown choice for continue prompt, aborting.")
            return
        
    elif command == 'clean':
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
        print("-------------------------------")
        print("WARNING: Cleaning will remove the directories './build' and './dist'.")
        cnt_clean = input("Continue with clean? [Y/N]: ")
        if cnt_clean.lower().startswith('y'):
            print("-------------------------------")
            clean_build()
        elif cnt_clean.lower().startswith('n'):
            print("Clean failed: Aborted by user.")
            return
        else:
            print("Clean failed: Unknown choice for continue prompt, aborting.")
            return

    elif command == 'version':
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
    
    else:
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
        print("-------------------------------")
        print(f"Unknown command '{command}'.")
        
        print("\nPossible commands:")
        print("  <no command>      --> start Lunite REPL CLI")
        print("  run <file.luna>   --> interpret a Lunite source code file")
        print("  build <file.luna> --> bind and compile code into an executable")
        print("  clean             --> deletes build directories")
        print("  version           --> display version information")

if __name__ == "__main__":
    main()
