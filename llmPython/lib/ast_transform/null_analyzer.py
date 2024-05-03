import ast
from . import Util
from . import scope_analyzer

class DependencyAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        self.passName = "dependency"
        super().__init__(copy) 

    def visit_arguments(self, node):
        super().visit_arguments(node)
        return node
    def visit_Assign(self, node):
        super().visit_Assign(node)
        return node
    def visit_AugAssign(self, node):
        super().visit_AugAssign(node)
        return node
    def visit_AnnAssign(self, node):
        super().visit_AnnAssign(node)
        return node
    def visit_ImportFrom(self, node):
        super().visit_ImportFrom(node)
        return node
    def visit_Import(self, node):
        super().visit_Import(node)
        return node
    def visit_Expr(self, node):
        super().visit_Expr(node)
        return node
    def visit_TypeAlias(self, node):
        super().visit_TypeAlias(node)
        return node
    def visit_TypeVar(self, node):
        super().visit_TypeVar(node)
        return node
    def visit_TypeVarTuple(self, node):
        super().visit_TypeVarTuple(node)
        return node
    def visit_ParamSpec(self, node):
        super().visit_ParamSpec(node)
        return node
    def visit_FunctionDef(self, node, is_async=False):
        super().visit_FunctionDef(node)
        return node
    def visit_AsyncFunctionDef(self, node):
        super().visit_AsyncFunctionDef(node)
        return node
    def visit_ClassDef(self, node):
        super().visit_ClassDef(node)
        return node
    def visit_If(self, node):
        super().visit_If(node)
        return node
    def visit_For(self, node, is_async=False):
        super().visit_For(node)
        return node
    def visit_AsyncFor(self, node):
        super().visit_AsyncFor(node)
        return node
    def visit_While(self, node):
        super().visit_While(node)
        return node
    def visit_With(self, node):
        super().visit_With(node)
        return node
    def visit_AsyncWith(self, node):
        super().visit_AsyncWith(node)
        return node
    def visit_withitem(self, node):
        super().visit_withitem(node)
        return node
    def visit_NameConstant(self, node):
        super().visit_NameConstant(node)
        return node
    def visit_Pass(self, node):
        super().visit_Pass(node)
        return node
    def visit_Print(self, node):
        super().visit_Print(node)
        return node
    def visit_Delete(self, node):
        super().visit_Delete(node)
        return node
    def visit_TryExcept(self, node):
        super().visit_TryExcept(node)
        return node
    def visit_Try(self, node):
        super().visit_Try(node)
        return node
    def visit_ExceptHandler(self, node):
        super().visit_ExceptHandler(node)
        return node
    def visit_TryFinally(self, node):
        super().visit_TryFinally(node)
        return node
    def visit_Exec(self, node):
        super().visit_Exec(node)
        return node
    def visit_Assert(self, node):
        super().visit_Assert(node)
        return node
    def visit_Global(self, node):
        super().visit_Global(node)
        return node
    def visit_Nonlocal(self, node):
        super().visit_Nonlocal(node)
        return node
    def visit_Return(self, node):
        super().visit_Return(node)
        return node
    def visit_Break(self, node):
        super().visit_Break(node)
        return node
    def visit_Continue(self, node):
        super().visit_Continue(node)
        return node
    def visit_Raise(self, node):
        super().visit_Raise(node)
        return node
    def visit_Match(self, node):
        super().visit_Match(node)
        return node
    def visit_match_case(self, node):
        super().visit_match_case(node)
        return node
    def visit_MatchSequence(self, node):
        super().visit_MatchSequence(node)
        return node
    def visit_MatchValue(self, node):
        super().visit_MatchValue(node)
        return node
    def visit_MatchSingleton(self, node):
        super().visit_MatchSingleton(node)
        return node
    def visit_MatchStar(self, node):
        super().visit_MatchStar(node)
        return node
    def visit_MatchMapping(self, node):
        super().visit_MatchMapping(node)
        return node
    def visit_MatchAs(self, node):
        super().visit_MatchAs(node)
        return node
    def visit_MatchOr(self, node):
        super().visit_MatchOr(node)
        return node
    def visit_MatchClass(self, node):
        super().visit_MatchClass(node)
        return node
    def visit_Attribute(self, node):
        super().visit_Attribute(node)
        return node
    def visit_Call(self, node, len=len):
        super().visit_Call(node)
        return node
    def visit_Name(self, node):
        super().visit_Name(node)
        return node
    def visit_Constant(self, node):
        super().visit_Constant(node)
        return node
    def visit_JoinedStr(self, node):
        super().visit_JoinedStr(node)
        return node
    def visit_Str(self, node):
        super().visit_Str(node)
        return node
    def visit_Bytes(self, node):
        super().visit_Bytes(node)
        return node
    def visit_Num(self, node):
        super().visit_Num(node)
        return node
    def visit_Tuple(self, node):
        super().visit_Tuple(node)
        return node
    def visit_List(self, node):
        super().visit_List(node)
        return node
    def visit_Set(self, node):
        super().visit_Set(node)
        return node
    def visit_Dict(self, node):
        super().visit_Dict(node)
        return node
    def visit_BinOp(self, node):
        super().visit_BinOp(node)
        return node
    def visit_BoolOp(self, node):
        super().visit_BoolOp(node)
        return node
    def visit_Compare(self, node):
        super().visit_Compare(node)
        return node
    def visit_NamedExpr(self, node):
        super().visit_NamedExpr(node)
        return node
    def visit_UnaryOp(self, node):
        super().visit_UnaryOp(node)
        return node
    def visit_Subscript(self, node):
        super().visit_Subscript(node)
        return node
    def visit_Slice(self, node):
        super().visit_Slice(node)
        return node
    def visit_Index(self, node):
        super().visit_Index(node)
        return node
    def visit_ExtSlice(self, node):
        super().visit_ExtSlice(node)
        return node
    def visit_Yield(self, node):
        super().visit_Yield(node)
        return node
    def visit_Await(self, node):
        super().visit_Await(node)
        return node
    def visit_Lambda(self, node):
        super().visit_Lambda(node)
        return node
    def visit_Ellipsis(self, node):
        super().visit_Ellipsis(node)
        return node
    def visit_ListComp(self, node):
        super().visit_ListComp(node)
        return node
    def visit_GeneratorExp(self, node):
        super().visit_GeneratorExp(node)
        return node
    def visit_SetComp(self, node):
        super().visit_SetComp(node)
        return node
    def visit_DictComp(self, node):
        super().visit_DictComp(node)
        return node
    def visit_IfExp(self, node):
        super().visit_IfExp(node)
        return node
    def visit_Starred(self, node):
        super().visit_Starred(node)
        return node
    def visit_Repr(self, node):
        super().visit_Repr(node)
        return node
    def visit_Expression(self, node):
        super().visit_Expression(node)
        return node
    def visit_arg(self, node):
        super().visit_arg(node)
        return node
    def visit_alias(self, node):
        super().visit_alias(node)
        return node
    def visit_comprehension(self, node):
        super().visit_comprehension(node)
        return node
    def visit_Module(self, node):
        super().visit_Module(node)
        return node


        
    def Scan(self,source):
        self.source = source
        self.visit(source)
      
def Scan(parent=None):
    analyzer = DependencyAnalyzer(parent)
    return analyzer

