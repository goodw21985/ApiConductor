import ast

from . import scope_analyzer


class DependencyAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        self.pass_name = "dependency"
        super().__init__(copy)

    def Endpath():
        raise ValueError

    def visit_arguments(self, node):
        self.generic_visit(node)
        return node

    def visit_Assign(self, node):
        self.visit(node.value)
        for t in node.targets:
            self.skip_visit(t)
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)  # AugAssign(node)
        return node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)  # AnnAssign(node)
        return node

    def visit_ImportFrom(self, node):
        self.generic_visit(node)  # ImportFrom(node)
        return node

    def visit_Import(self, node):
        self.generic_visit(node)  # Import(node)
        return node

    def visit_Expr(self, node):
        self.generic_visit(node)  # Expr(node)
        return node

    def visit_TypeAlias(self, node):
        self.generic_visit(node)  # TypeAlias(node)
        return node

    def visit_TypeVar(self, node):
        self.generic_visit(node)  # TypeVar(node)
        return node

    def visit_TypeVarTuple(self, node):
        self.generic_visit(node)  # TypeVarTuple(node)
        return node

    def visit_ParamSpec(self, node):
        self.generic_visit(node)  # ParamSpec(node)
        return node

    def visit_FunctionDef(self, node, is_async=False):
        self.generic_visit(node)  # FunctionDef(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)  # AsyncFunctionDef(node)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)  # ClassDef(node)
        return node

    def visit_If(self, node):
        self.generic_visit(node)  # If(node)
        return node

    def visit_For(self, node, is_async=False):
        self.generic_visit(node)  # For(node)
        return node

    def visit_AsyncFor(self, node):
        self.generic_visit(node)  # AsyncFor(node)
        return node

    def visit_While(self, node):
        self.generic_visit(node)  # While(node)
        return node

    def visit_With(self, node):
        self.generic_visit(node)  # With(node)
        return node

    def visit_AsyncWith(self, node):
        self.generic_visit(node)  # AsyncWith(node)
        return node

    def visit_withitem(self, node):
        self.generic_visit(node)  # withitem(node)
        return node

    def visit_NameConstant(self, node):
        self.generic_visit(node)  # NameConstant(node)
        return node

    def visit_Pass(self, node):
        self.generic_visit(node)  # Pass(node)
        return node

    def visit_Print(self, node):
        self.generic_visit(node)  # Print(node)
        return node

    def visit_Delete(self, node):
        self.generic_visit(node)  # Delete(node)
        return node

    def visit_TryExcept(self, node):
        self.generic_visit(node)  # TryExcept(node)
        return node

    def visit_Try(self, node):
        self.generic_visit(node)  # Try(node)
        return node

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)  # ExceptHandler(node)
        return node

    def visit_TryFinally(self, node):
        self.generic_visit(node)  # TryFinally(node)
        return node

    def visit_Exec(self, node):
        self.generic_visit(node)  # Exec(node)
        return node

    def visit_Assert(self, node):
        self.generic_visit(node)  # Assert(node)
        return node

    def visit_Global(self, node):
        return node

    def visit_Nonlocal(self, node):
        return node

    def visit_Return(self, node):
        self.generic_visit(node)
        return node

    def visit_Break(self, node):
        self.generic_visit(node)  # Break(node)
        return node

    def visit_Continue(self, node):
        self.generic_visit(node)  # Continue(node)
        return node

    def visit_Raise(self, node):
        self.generic_visit(node)  # Raise(node)
        return node

    def visit_Match(self, node):
        self.generic_visit(node)  # Match(node)
        return node

    def visit_match_case(self, node):
        self.generic_visit(node)  # match_case(node)
        return node

    def visit_MatchSequence(self, node):
        self.generic_visit(node)  # MatchSequence(node)
        return node

    def visit_MatchValue(self, node):
        self.generic_visit(node)  # MatchValue(node)
        return node

    def visit_MatchSingleton(self, node):
        self.generic_visit(node)  # MatchSingleton(node)
        return node

    def visit_MatchStar(self, node):
        self.generic_visit(node)  # MatchStar(node)
        return node

    def visit_MatchMapping(self, node):
        self.generic_visit(node)  # MatchMapping(node)
        return node

    def visit_MatchAs(self, node):
        self.generic_visit(node)  # MatchAs(node)
        return node

    def visit_MatchOr(self, node):
        self.generic_visit(node)  # MatchOr(node)
        return node

    def visit_MatchClass(self, node):
        self.generic_visit(node)  # MatchClass(node)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)  # Attribute(node)
        return node

    def visit_Call2(self, node, len=len):
        # cannot be delegate
        if not isinstance(node.func, ast.Name):
            self.EndPath()
            
        # any if conditions in the ifstack become depenedencies any target
        for if_parent in self.current_node_lookup.if_stack:
            conditions = if_parent.if_frame.conditions[:if_parent.blockIndex+1]
            for condition in conditions:
                self.visit(condition)
                
        return node

    def visit_Name2(self, node):
        if node.id == "sum2":
            node = node
        s = self.current_node_lookup
        for writer in s.symbol.write:
            if len(writer) > 1:
                self.visit(writer[-2])
        for writer in s.symbol.readwrite:
            if len(writer) > 1:
                self.visit(writer[-2])
        return node

    def visit_Constant(self, node):
        self.generic_visit(node)  # Constant(node)
        return node

    def visit_JoinedStr(self, node):
        self.generic_visit(node)  # JoinedStr(node)
        return node

    def visit_Str(self, node):
        self.generic_visit(node)  # Str(node)
        return node

    def visit_Bytes(self, node):
        self.generic_visit(node)  # Bytes(node)
        return node

    def visit_Num(self, node):
        self.generic_visit(node)
        return node

    def visit_Tuple(self, node):
        self.generic_visit(node)  # Tuple(node)
        return node

    def visit_List(self, node):
        self.generic_visit(node)  # List(node)
        return node

    def visit_Set(self, node):
        self.generic_visit(node)  # Set(node)
        return node

    def visit_Dict(self, node):
        self.generic_visit(node)  # Dict(node)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        return node

    def visit_NamedExpr(self, node):
        self.generic_visit(node)  # NamedExpr(node)
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)  # UnaryOp(node)
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)  # Subscript(node)
        return node

    def visit_Slice(self, node):
        self.generic_visit(node)  # Slice(node)
        return node

    def visit_Index(self, node):
        self.generic_visit(node)  # Index(node)
        return node

    def visit_ExtSlice(self, node):
        self.generic_visit(node)  # ExtSlice(node)
        return node

    def visit_Yield(self, node):
        self.generic_visit(node)  # Yield(node)
        return node

    def visit_Await(self, node):
        self.generic_visit(node)  # Await(node)
        return node

    def visit_Lambda(self, node):
        self.generic_visit(node)  # Lambda(node)
        return node

    def visit_Ellipsis(self, node):
        self.generic_visit(node)  # Ellipsis(node)
        return node

    def visit_ListComp(self, node):
        self.generic_visit(node)
        return node

    def visit_GeneratorExp(self, node):
        self.generic_visit(node)  # GeneratorExp(node)
        return node

    def visit_SetComp(self, node):
        self.generic_visit(node)  # SetComp(node)
        return node

    def visit_DictComp(self, node):
        self.generic_visit(node)  # DictComp(node)
        return node

    def visit_IfExp(self, node):
        self.generic_visit(node)  # IfExp(node)
        return node

    def visit_Starred(self, node):
        self.generic_visit(node)  # Starred(node)
        return node

    def visit_Repr(self, node):
        self.generic_visit(node)  # Repr(node)
        return node

    def visit_Expression(self, node):
        self.generic_visit(node)  # Expression(node)
        return node

    def visit_arg(self, node):
        self.generic_visit(node)  # arg(node)
        return node

    def visit_alias(self, node):
        self.generic_visit(node)  # alias(node)
        return node

    def visit_comprehension(self, node):
        self.generic_visit(node)
        return node

    def visit_Module(self, node):
        self.generic_visit(node)  # Module(node)
        return node

    def HasSingleSimpleWrite(self, symbolTableEntry):
        return (
            len(symbolTableEntry.write) == 1
            and not symbolTableEntry.readwrite
            and not symbolTableEntry.declared
            and not symbolTableEntry.ambiguous
        )

    def FindTerminalNodes(self):
        self.terminal_nodes = []
        if self.global_return_statement is not None:
            self.terminal_nodes.append(self.global_return_statement)
        else:
            for symbol in self.symbol_table.keys():
                record = self.symbol_table[symbol]
                if (
                    not record.child
                    and record.write
                    and not record.read
                    and len(record.write) == 1
                ):
                    self.terminal_nodes.append(record.write[0][-1])
        if len(self.terminal_nodes) == 0:
            for node in self.critical_nodes:
                self.terminal_nodes.append(node)
        for v in self.terminal_nodes:
            if v not in self.critical_nodes:
                self.critical_nodes.append(v)
                self.critical_node_names[v]=self.new_critical_node_name()

    def MarkDependencies(self, critical_node):
        self.tracking = critical_node
        self.visit(self.tracking)

    def CreateDependencyGraphForCriticalNodes():
        pass
    
    def track_dependency(self, node):
        self.current_node_lookup.dependency_visited = True

        if self.tracking in self.current_node_lookup.dependency:
            # stop when we hit the same node
            return True
        elif node != self.tracking:
            self.current_node_lookup.dependency.append(self.tracking)

        if node != self.tracking and node in self.critical_nodes:
            # stop when we see another critical node
            return True

        return False


def Scan(tree, parent=None):
    analyzer = DependencyAnalyzer(parent)
    analyzer.FindTerminalNodes()
    for critical_node in analyzer.critical_nodes:
        analyzer.MarkDependencies(critical_node)

    return analyzer
