# Parser
# ------

from core.constants import *
from core.errors import *
from core.ast import *

# ==========================================
# PARSER
# ==========================================

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos]
    
    def _advance_loc(self, line, col, text):
        for char in text:
            if char == '\n':
                line += 1
                col = 1
            else:
                col += 1
        return line, col

    def _unescape_fstring_part(self, text, line, col):
        s = ""
        i = 0
        n = len(text)
        escape_map = {
            'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'",
            'b': '\b', 'h': '\t', '0': '\0'
        }
        
        while i < n:
            char = text[i]
            if char == '\\' and i + 1 < n:
                next_char = text[i+1]
                if next_char == 'u':
                    if i + 5 < n:
                        try:
                            hex_str = text[i+2:i+6]
                            s += chr(int(hex_str, 16))
                            i += 6
                            continue
                        except ValueError:
                            raise lunite_error("Syntax", f"Invalid Unicode sequence in f-string", line, col)
                
                if next_char in escape_map:
                    s += escape_map[next_char]
                    i += 2
                else:
                    s += '\\'
                    i += 1
            else:
                s += char
                i += 1
        return s

    def is_case_start(self):
        if self.pos >= len(self.tokens):
            return False
            
        i = self.pos
        tok = self.tokens[i]
        
        valid_start = tok.type in (TOKEN_INT, TOKEN_FLOAT, TOKEN_STRING, TOKEN_CHAR, TOKEN_ID, TOKEN_KEYWORD, TOKEN_LBRACKET, TOKEN_LBRACE, TOKEN_MINUS)
        if not valid_start:
            return False
        
        if i + 1 < len(self.tokens) and self.tokens[i+1].type == TOKEN_COLON:
            return True
            
        if tok.type == TOKEN_ID and i + 3 < len(self.tokens):
            if self.tokens[i+1].type == TOKEN_DOT and self.tokens[i+2].type == TOKEN_ID and self.tokens[i+3].type == TOKEN_COLON:
                return True
        
        return False

    def eat(self, token_type):
        token = self.current_token
        if self.current_token.type == token_type:
            self.pos += 1
            if self.pos < len(self.tokens):
                self.current_token = self.tokens[self.pos]
        else:
            raise lunite_error("Syntax", f"Unexpected token {self.current_token.type}, expected {token_type}", token.line, token.col)

    def peek(self):
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return self.current_token
    
    def parse_args(self):
        args = []
        if self.current_token.type != TOKEN_RPAREN:
            if self.current_token.type == TOKEN_ID and self.peek().type == TOKEN_ASSIGN:
                id_token = self.current_token
                self.eat(TOKEN_ID)
                self.eat(TOKEN_ASSIGN)
                val = self.expr()
                
                id_node = Identifier(id_token)
                id_node.line = id_token.line
                id_node.col = id_token.col
                
                node = Assign(id_node, val)
                node.line = id_token.line
                node.col = id_token.col
                args.append(node)
            else:
                args.append(self.expr())

            while self.current_token.type == TOKEN_COMMA:
                self.eat(TOKEN_COMMA)
                if self.current_token.type == TOKEN_ID and self.peek().type == TOKEN_ASSIGN:
                    id_token = self.current_token
                    self.eat(TOKEN_ID)
                    self.eat(TOKEN_ASSIGN)
                    val = self.expr()
                    
                    id_node = Identifier(id_token)
                    id_node.line = id_token.line
                    id_node.col = id_token.col
                    
                    node = Assign(id_node, val)
                    node.line = id_token.line
                    node.col = id_token.col
                    args.append(node)
                else:
                    args.append(self.expr())
        return args

    def atom(self):
        token = self.current_token
        
        if token.type == TOKEN_INT or token.type == TOKEN_FLOAT:
            self.eat(token.type)
            node = Number(token)
            node.line = token.line
            node.col = token.col
            return node
        
        elif token.type == TOKEN_CHAR:
            self.eat(TOKEN_CHAR)
            node = Char(token)
            node.line = token.line
            node.col = token.col
            return node
        
        elif token.type == TOKEN_FSTRING:
            self.eat(TOKEN_FSTRING)
            
            raw_val = token.value
            if not raw_val:
                return String(Token(TOKEN_STRING, "", token.line, token.col))
            
            parts = []
            current_str = ""
            depth = 0
            expr_buffer = ""
            
            i = 0
            while i < len(raw_val):
                char = raw_val[i]
                
                if char == '{':
                    if depth == 0:
                        if current_str:
                            parts.append(("str", current_str))
                            current_str = ""
                        depth = 1
                    else:
                        expr_buffer += char
                        depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        parts.append(("expr", expr_buffer))
                        expr_buffer = ""
                    else:
                        expr_buffer += char
                else:
                    if depth > 0:
                        expr_buffer += char
                    else:
                        current_str += char
                i += 1
            
            if current_str:
                parts.append(("str", current_str))

            curr_line = token.line
            curr_col = token.col + 2
            
            root = String(Token(TOKEN_STRING, "", token.line, token.col))
            root.line = token.line
            root.col = token.col
            
            for p_type, p_val in parts:
                if p_type == "str":
                    unescaped = self._unescape_fstring_part(p_val, curr_line, curr_col)
                    lit = String(Token(TOKEN_STRING, unescaped, curr_line, curr_col))
                    lit.line = curr_line
                    lit.col = curr_col
                    
                    add_op = Token(TOKEN_PLUS, '+', curr_line, curr_col)
                    root = BinaryOp(root, add_op, lit)
                    root.line = curr_line
                    root.col = curr_col
                    
                    curr_line, curr_col = self._advance_loc(curr_line, curr_col, p_val)
                    
                elif p_type == "expr":
                    sub_lexer = Lexer(p_val, start_line=curr_line, start_col=curr_col + 1)
                    sub_tokens = []
                    while True:
                        t = sub_lexer.get_next_token()
                        sub_tokens.append(t)
                        if t.type == TOKEN_EOF: break
                    
                    sub_parser = Parser(sub_tokens)
                    sub_expr = sub_parser.expr()
                    
                    str_call = FunctionCall('str', [sub_expr])
                    str_call.line = curr_line
                    str_call.col = curr_col
                    
                    add_op = Token(TOKEN_PLUS, '+', curr_line, curr_col)
                    root = BinaryOp(root, add_op, str_call)
                    root.line = curr_line
                    root.col = curr_col
                    
                    curr_line, curr_col = self._advance_loc(curr_line, curr_col, "{" + p_val + "}")

            return root
        
        elif token.type == TOKEN_STRING:
            self.eat(TOKEN_STRING)
            node = String(token)
            node.line = token.line
            node.col = token.col
            return node
        
        elif token.type == TOKEN_KEYWORD and token.value == 'true':
            self.eat(TOKEN_KEYWORD)
            node = Boolean(token, True)
            node.line = token.line
            node.col = token.col
            return node
        
        elif token.type == TOKEN_KEYWORD and token.value == 'false':
            self.eat(TOKEN_KEYWORD)
            node = Boolean(token, False)
            node.line = token.line
            node.col = token.col
            return node
        
        elif token.type == TOKEN_KEYWORD and token.value == 'null':
            self.eat(TOKEN_KEYWORD)
            node = Null()
            node.line = token.line
            node.col = token.col
            return node
            
        elif token.type == TOKEN_LBRACKET:
            self.eat(TOKEN_LBRACKET)
            elements = []
            if self.current_token.type != TOKEN_RBRACKET:
                elements.append(self.expr())
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    elements.append(self.expr())
            self.eat(TOKEN_RBRACKET)
            node = ListLiteral(elements)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_LBRACE:
            self.eat(TOKEN_LBRACE)
            if self.current_token.type == TOKEN_RBRACE:
                self.eat(TOKEN_RBRACE)
                node = DictLiteral([])
                node.line = token.line
                node.col = token.col
                return node
            
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
                node = DictLiteral(pairs)
                node.line = token.line
                node.col = token.col
                return node
            else:
                elements = [first]
                while self.current_token.type == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    elements.append(self.expr())
                self.eat(TOKEN_RBRACE)
                node = SetLiteral(elements)
                node.line = token.line
                node.col = token.col
                return node

        elif token.type == TOKEN_KEYWORD and token.value == 'new':
            self.eat(TOKEN_KEYWORD)
            
            if self.current_token.type != TOKEN_ID:
                 raise lunite_error("Syntax", "Expected class name after 'new'", self.current_token.line, self.current_token.col)
            
            node = Identifier(self.current_token)
            node.line = self.current_token.line
            node.col = self.current_token.col
            self.eat(TOKEN_ID)
            
            while self.current_token.type == TOKEN_DOT:
                self.eat(TOKEN_DOT)
                if self.current_token.type != TOKEN_ID:
                    raise lunite_error("Syntax", "Expected identifier after dot", self.current_token.line, self.current_token.col)
                member_name = self.current_token.value
                
                prev_node = node
                node = MemberAccess(prev_node, member_name)
                node.line = prev_node.line
                node.col = prev_node.col
                self.eat(TOKEN_ID)

            self.eat(TOKEN_LPAREN)
            args = self.parse_args()
            self.eat(TOKEN_RPAREN)
            
            result_node = NewInstance(node, args)
            result_node.line = token.line
            result_node.col = token.col
            return result_node
        
        elif token.type == TOKEN_KEYWORD and token.value == 'in':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            args = self.parse_args()
            self.eat(TOKEN_RPAREN)
            node = FunctionCall('in', args)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_ID:
            name = token.value
            self.eat(TOKEN_ID)
            if self.current_token.type == TOKEN_LPAREN:
                self.eat(TOKEN_LPAREN)
                args = self.parse_args()
                self.eat(TOKEN_RPAREN)
                return FunctionCall(name, args)
            node = Identifier(token)
            node.line = token.line
            node.col = token.col
            return node
        
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
                node = TupleLiteral([])
                node.line = token.line
                node.col = token.col
                return node
            
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
                        raise lunite_error("Syntax", "Lambda parameters must be identifiers", self.current_token.line, self.current_token.col)
                
                if self.current_token.type == TOKEN_LBRACE:
                    self.eat(TOKEN_LBRACE)
                    body = self.block()
                    self.eat(TOKEN_RBRACE)
                    node = LambdaExpr(params, body)
                else:
                    node = LambdaExpr(params, self.expr())

                node.line = token.line
                node.col = token.col
                return node

            if len(exprs) == 1: return exprs[0]
            node = TupleLiteral(exprs)
            node.line = token.line
            node.col = token.col
            return node
        
        raise lunite_error("Syntax", f"Invalid atom '{token.value}'", token.line, token.col)

    def factor(self):
        token = self.current_token
        
        if token.type in (TOKEN_PLUS, TOKEN_MINUS, TOKEN_BIT_NOT, TOKEN_NOT, TOKEN_INC, TOKEN_DEC):
            self.eat(token.type)
            
            if token.type in (TOKEN_INC, TOKEN_DEC):
                target = self.factor()
                node = UpdateExpr(target, token, True)
            else:
                node = UnaryOp(op=token, expr=self.factor())
                
            node.line = token.line
            node.col = token.col
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
                    node.line = self.current_token.line
                    node.col = self.current_token.col
                else:
                    node = MemberAccess(node, member_name)
                    node.line = self.current_token.line
                    node.col = self.current_token.col
            
            elif self.current_token.type == TOKEN_LBRACKET:
                self.eat(TOKEN_LBRACKET)
                
                start = None
                end = None
                is_slice = False
                
                if self.current_token.type == TOKEN_COLON:
                    is_slice = True
                    self.eat(TOKEN_COLON)
                    if self.current_token.type != TOKEN_RBRACKET:
                        end = self.expr()
                else:
                    start = self.expr()
                    
                    if self.current_token.type == TOKEN_COLON:
                        is_slice = True
                        self.eat(TOKEN_COLON)
                        if self.current_token.type != TOKEN_RBRACKET:
                            end = self.expr()
                
                self.eat(TOKEN_RBRACKET)
                
                if is_slice:
                    node = SliceAccess(node, start, end)
                    node.line = token.line
                    node.col = token.col
                else:
                    node = IndexAccess(node, start)
                    node.line = token.line
                    node.col = token.col
        
        if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
            op_token = self.current_token
            self.eat(op_token.type)
            node = UpdateExpr(node, op_token, False)
            node.line = op_token.line
            node.col = op_token.col

        return node

    def term(self):
        node = self.factor()
        while self.current_token.type in (TOKEN_MUL, TOKEN_DIV, TOKEN_MOD):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.factor())
            node.line = token.line
            node.col = token.col
        return node
    
    def math_expr(self):
        node = self.term()
        while self.current_token.type in (TOKEN_PLUS, TOKEN_MINUS, TOKEN_EQ, TOKEN_NEQ, TOKEN_GT, TOKEN_LT, TOKEN_GE, TOKEN_LE):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.term())
            node.line = token.line
            node.col = token.col
        return node
    
    def shift_expr(self):
        node = self.math_expr()
        while self.current_token.type in (TOKEN_LSHIFT, TOKEN_RSHIFT):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.math_expr())
            node.line = token.line
            node.col = token.col
        return node
    
    def bitwise_and_expr(self):
        node = self.shift_expr()
        while self.current_token.type == TOKEN_BIT_AND:
            token = self.current_token
            self.eat(TOKEN_BIT_AND)
            node = BinaryOp(left=node, op=token, right=self.shift_expr())
            node.line = token.line
            node.col = token.col
        return node

    def bitwise_xor_expr(self):
        node = self.bitwise_and_expr()
        while self.current_token.type == TOKEN_BIT_XOR:
            token = self.current_token
            self.eat(TOKEN_BIT_XOR)
            node = BinaryOp(left=node, op=token, right=self.bitwise_and_expr())
            node.line = token.line
            node.col = token.col
        return node

    def bitwise_or_expr(self):
        node = self.bitwise_xor_expr()
        while self.current_token.type == TOKEN_BIT_OR:
            token = self.current_token
            self.eat(TOKEN_BIT_OR)
            node = BinaryOp(left=node, op=token, right=self.bitwise_xor_expr())
            node.line = token.line
            node.col = token.col
        return node
    
    def comp_expr(self):
        node = self.bitwise_or_expr()
        while self.current_token.type in (TOKEN_EQ, TOKEN_NEQ, TOKEN_GT, TOKEN_LT, TOKEN_LE, TOKEN_GE, TOKEN_IS, TOKEN_KEYWORD):
            token = self.current_token
            if token.type == TOKEN_KEYWORD and token.value == 'in':
                self.eat(TOKEN_KEYWORD)
                right = self.bitwise_or_expr()
                node = BinaryOp(left=node, op=token, right=right) 
                node.line = token.line
                node.col = token.col
                continue
            if token.type == TOKEN_KEYWORD and token.value != 'in':
                break
            self.eat(token.type)
            if token.type == TOKEN_IS:
                target = self.bitwise_or_expr()
                node = TypeCheckOp(node, target)
                node.line = token.line
                node.col = token.col
            else:
                node = BinaryOp(left=node, op=token, right=self.bitwise_or_expr())
                node.line = token.line
                node.col = token.col
        return node

    def logic_expr(self):
        node = self.comp_expr()
        while self.current_token.type in (TOKEN_AND, TOKEN_OR):
            token = self.current_token
            self.eat(token.type)
            node = BinaryOp(left=node, op=token, right=self.comp_expr())
            node.line = token.line
            node.col = token.col
        return node

    def expr(self):
        token = self.current_token
        node = self.logic_expr()
        
        if self.current_token.type == TOKEN_QUESTION:
            self.eat(TOKEN_QUESTION)
            true_expr = self.expr()
            self.eat(TOKEN_COLON)
            false_expr = self.expr()
            node = TernaryOp(node, true_expr, false_expr)
        
        node.line = token.line
        node.col = token.col
        return node

    def _parse_modifiers(self):
        is_public = True
        is_global = False
        is_const = False

        is_public_kw = False
        is_private_kw = False
        is_global_kw = False
        is_const_kw = False

        while self.current_token.type == TOKEN_KEYWORD:
            val = self.current_token.value
            if val == 'public':
                if is_private_kw:
                    raise lunite_error("Syntax", "Cannot use 'public' with 'private'")
                if is_public_kw:
                    raise lunite_error("Syntax", "Duplicate 'public'")
                is_public = True
                is_public_kw = True
                self.eat(TOKEN_KEYWORD)
            elif val == 'private':
                if is_public_kw:
                    raise lunite_error("Syntax", "Cannot use 'private' with 'public'")
                if is_private_kw:
                    raise lunite_error("Syntax", "Duplicate 'private'")
                is_public = False
                is_private_kw = True
                self.eat(TOKEN_KEYWORD)
            elif val == 'global':
                if is_global_kw:
                    raise lunite_error("Syntax", "Duplicate 'global'")
                is_global = True
                is_global_kw = True
                self.eat(TOKEN_KEYWORD)
            elif val == 'const':
                if is_const_kw:
                    raise lunite_error("Syntax", "Duplicate 'const'")
                is_const = True
                is_const_kw = True
                self.eat(TOKEN_KEYWORD)
            else:
                break
        return is_public, is_global, is_const

    def parse_statement(self):
        start_line = self.current_token.line
        start_col = self.current_token.col
        
        node = self._parse_statement_body()
        
        if isinstance(node, AST):
            node.line = start_line
            node.col = start_col
        return node

    def _parse_statement_body(self):
        token = self.current_token
        
        if token.type == TOKEN_KEYWORD and token.value == 'import':
            self.eat(TOKEN_KEYWORD)
            module_name = ""
            
            if self.current_token.type == TOKEN_ID:
                module_name = self.current_token.value
                self.eat(TOKEN_ID)
            elif self.current_token.type == TOKEN_STRING:
                module_name = self.current_token.value
                self.eat(TOKEN_STRING)
            else:
                raise lunite_error("Syntax", "Expected module name after 'import'", token.line, token.col)
            
            source_package = None
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'from':
                self.eat(TOKEN_KEYWORD)
                if self.current_token.type == TOKEN_STRING:
                    source_package = self.current_token.value
                    self.eat(TOKEN_STRING)
                elif self.current_token.type == TOKEN_ID:
                    source_package = self.current_token.value
                    self.eat(TOKEN_ID)
                else:
                    raise lunite_error("Syntax", "Expected package name after 'from'", self.current_token.line, self.current_token.col)

            node = ImportStatement(module_name, source_package)
            node.line = token.line
            node.col = token.col
            return node
            
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
                raise lunite_error("Syntax", "Expected Python module name after 'import_py'", token.line, token.col)
            
            source_package = None
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'from':
                self.eat(TOKEN_KEYWORD)
                if self.current_token.type == TOKEN_STRING:
                    source_package = self.current_token.value
                    self.eat(TOKEN_STRING)
                elif self.current_token.type == TOKEN_ID:
                    source_package = self.current_token.value
                    self.eat(TOKEN_ID)
                else:
                    raise lunite_error("Import", "Expected Python package name after 'from'", self.current_token.line, self.current_token.col)
            
            node = ImportPyStatement(name, alias=name, source_package=source_package)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and (token.value == 'let' or token.value == 'const'):
            is_const_initial = (token.value == 'const')
            self.eat(TOKEN_KEYWORD)

            is_public, is_global, is_const_mod = self._parse_modifiers()
            is_const = is_const_initial or is_const_mod
            
            if not is_const and self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'const':
                self.eat(TOKEN_KEYWORD)
                is_const = True

            if self.current_token.type == TOKEN_LBRACKET:
                self.eat(TOKEN_LBRACKET)
                is_public, is_global, is_const_mod = self._parse_modifiers()
                is_const = is_const_initial or is_const_mod
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
                node = DestructuringDecl(names, val, is_const, is_public, is_global)
                node.line = token.line
                node.col = token.col
                return node

            var_name = self.current_token.value
            self.eat(TOKEN_ID)
            
            if self.current_token.type == TOKEN_ASSIGN:
                self.eat(TOKEN_ASSIGN)
                val = self.expr()
            else:
                val = Null()
                val.line = token.line
                val.col = token.col

            node = VarDecl(var_name, val, is_const, is_public, is_global)
            node.line = token.line
            node.col = token.col
            return node
        
        elif token.type == TOKEN_KEYWORD and token.value == 'func':
            self.eat(TOKEN_KEYWORD)
            is_public, is_global, _ = self._parse_modifiers()

            func_name = self.current_token.value
            self.eat(TOKEN_ID)
            self.eat(TOKEN_LPAREN)
            
            params = []
            if self.current_token.type != TOKEN_RPAREN:
                p_name = self.current_token.value
                self.eat(TOKEN_ID)
                p_def = None
                if self.current_token.type == TOKEN_ASSIGN:
                    self.eat(TOKEN_ASSIGN)
                    p_def = self.expr()
                params.append((p_name, p_def))
                
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
            node = FunctionDef(func_name, params, body, is_public, is_global)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'class':
            self.eat(TOKEN_KEYWORD)
            is_public, is_global, _ = self._parse_modifiers()

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
            
            node = ClassDef(class_name, body, superclass, is_public, is_global)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'return':
            self.eat(TOKEN_KEYWORD)
            val = self.expr()
            node = ReturnStatement(val)
            node.line = token.line
            node.col = token.col
            return node

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
                
                if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'if':
                    stmt = self.parse_statement()
                    false_block = Block([stmt])
                    false_block.line = stmt.line
                else:
                    self.eat(TOKEN_LBRACE)
                    false_block = self.block()
                    self.eat(TOKEN_RBRACE)
            
            node = IfStatement(cond, true_block, false_block)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'while':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            cond = self.expr()
            self.eat(TOKEN_RPAREN)
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            node = WhileStatement(cond, body)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'for':
            self.eat(TOKEN_KEYWORD)
            iter_name = self.current_token.value
            self.eat(TOKEN_ID)
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'in':
                self.eat(TOKEN_KEYWORD)
            else:
                raise lunite_error("Syntax", "Expected 'in' after 'for'", token.line, token.col)
            iterable = self.expr()
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            node = ForStatement(iter_name, iterable, body)
            node.line = token.line
            node.col = token.col
            return node

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
            else:
                raise lunite_error("Syntax", "Expected 'rescue' after 'attempt'", token.line, token.col)
            
            finally_block = None
            if self.current_token.type == TOKEN_KEYWORD and self.current_token.value == 'finally':
                self.eat(TOKEN_KEYWORD)
                self.eat(TOKEN_LBRACE)
                finally_block = self.block()
                self.eat(TOKEN_RBRACE)
            
            node = TryCatchStatement(try_block, error_var, catch_block, finally_block)
            node.line = token.line
            node.col = token.col
            return node
            
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
            node = EnumDef(name, members)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'break':
            self.eat(TOKEN_KEYWORD)
            node = BreakStatement()
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'advance':
            self.eat(TOKEN_KEYWORD)
            node = AdvanceStatement()
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'leap':
            self.eat(TOKEN_KEYWORD)
            if self.current_token.type == TOKEN_ID:
                target = Identifier(self.current_token)
                self.eat(TOKEN_ID)
                node = LeapStatement(target)
            elif self.current_token.type == TOKEN_INT:
                target = Number(self.current_token)
                self.eat(TOKEN_INT)
                node = LeapStatement(target)
            else:
                raise lunite_error("Syntax", "Expected label name or line number after 'leap'", token.line, token.col)
            node.line = token.line
            node.col = token.col
            return node
    
        elif token.type == TOKEN_LBRACE:
            if (self.pos + 1 < len(self.tokens) and 
                self.tokens[self.pos+1].type == TOKEN_ID and 
                self.pos + 2 < len(self.tokens) and 
                self.tokens[self.pos+2].type == TOKEN_RBRACE):
                
                self.eat(TOKEN_LBRACE)
                name = self.current_token.value
                self.eat(TOKEN_ID)
                self.eat(TOKEN_RBRACE)
                node = LabelDef(name)
                node.line = token.line
                node.col = token.col
                return node
            
            self.eat(TOKEN_LBRACE)
            body = self.block()
            self.eat(TOKEN_RBRACE)
            body.line = token.line
            body.col = token.col
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
                        
                        if self.current_token.type == TOKEN_COLON:
                            break

                        stmts.append(self.parse_statement())
                    
                    cases.append(MatchCase(val, Block(stmts)))

            self.eat(TOKEN_RBRACE)
            node = MatchStatement(subject, cases, default_block)
            node.line = token.line
            node.col = token.col
            return node

        elif token.type == TOKEN_KEYWORD and token.value == 'assert':
            self.eat(TOKEN_KEYWORD)
            self.eat(TOKEN_LPAREN)
            cond = self.expr()
            msg = None
            if self.current_token.type == TOKEN_COMMA:
                self.eat(TOKEN_COMMA)
                msg = self.expr()
            self.eat(TOKEN_RPAREN)
            
            node = AssertStatement(cond, msg)
            node.line = token.line
            node.col = token.col
            return node

        else:
            expr_node = self.expr()
            
            if self.current_token.type == TOKEN_ASSIGN:
                self.eat(TOKEN_ASSIGN)
                val = self.expr()
                node = Assign(expr_node, val)
                node.line = token.line
                node.col = token.col
                return node
            
            elif self.current_token.type in (TOKEN_PLUSEQ, TOKEN_MINUSEQ, TOKEN_MULEQ, TOKEN_DIVEQ, TOKEN_MODEQ):
                op = self.current_token
                self.eat(op.type)
                val = self.expr()
                node = CompoundAssign(expr_node, op, val)
                node.line = token.line
                node.col = token.col
                return node
                
            return expr_node
    
    def block(self):
        statements = []
        while self.current_token.type != TOKEN_RBRACE and self.current_token.type != TOKEN_EOF:
            if self.current_token.type == TOKEN_SEMI:
                self.eat(TOKEN_SEMI)
                continue
            
            statements.append(self.parse_statement())
            if self.current_token.type == TOKEN_SEMI:
                self.eat(TOKEN_SEMI)
                
        node = Block(statements)
        node.line = self.current_token.line
        node.col = self.current_token.col
        return node

    def parse(self):
        statements = []
        while self.current_token.type != TOKEN_EOF:
            if self.current_token.type == TOKEN_SEMI:
                self.eat(TOKEN_SEMI)
                continue

            statements.append(self.parse_statement())
            if self.current_token.type == TOKEN_SEMI:
                self.eat(TOKEN_SEMI)
                
        node = Block(statements)
        if statements:
            node.line = statements[0].line
            node.col = statements[0].col
        return node
