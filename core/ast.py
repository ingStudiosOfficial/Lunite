# Abstract Syntax Tree
# --------------------

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.lexer import *

# ==========================================
# AST NODES
# ==========================================

@dataclass
class AST:
    line: int = field(default=0, init=False)
    col: int = field(default=0, init=False)

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
    is_public: bool = True
    is_global: bool = False
    source_file: str = ""
    interpreter: Optional[Any] = None

    def __call__(self, *args, **kwargs):
        if self.interpreter:
            return self.interpreter.execute_node_as_call(self, list(args), kwargs)
        else:
            raise RuntimeError("No interpreter attached to this function")

@dataclass
class DecoratedFunc(AST):
    decorator: AST
    function: FunctionDef

@dataclass
class ClassDef(AST):
    name: str
    body: Block
    superclass: Optional[str]
    is_public: bool = True
    is_global: bool = False
    source_file: str = ""

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
    finally_block: Optional[Block] = None

@dataclass
class ImportStatement(AST):
    module_name: str
    source_package: Optional[str] = None

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
    is_public: bool = True
    is_global: bool = False

@dataclass
class NewInstance(AST):
    class_expr: AST
    args: List[AST]

@dataclass
class ImportPyStatement(AST):
    module_name: str
    alias: str
    source_package: Optional[str] = None

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
    is_public: bool = True
    is_global: bool = False

@dataclass
class SliceAccess(AST):
    target: AST
    start: Optional[AST]
    end: Optional[AST]

@dataclass
class AssertStatement(AST):
    condition: AST
    message: Optional[AST]

@dataclass
class UpdateExpr(AST):
    target: AST
    op: Token
    is_prefix: bool

@dataclass
class AsyncFuncDef(AST):
    name: str
    params: List[Tuple[str, Optional[AST]]]
    body: AST

@dataclass
class AwaitExpr(AST):
    expr: AST