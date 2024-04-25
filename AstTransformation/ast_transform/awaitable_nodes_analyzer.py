import ast
from . import Util
from . import scope_analyzer

class AwaitableNodesAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, awaitable_function_list, copy):
        super().__init__(copy) 
        self.awaitable_function_list = awaitable_function_list
        self.awaitable_nodes =[]

    # note... awaitable functions are always without a namespace, and we are not worrying about scope.
    def visit_Call2(self, node):
       if isinstance(node.func, ast.Name):
            if (node.func.id in self.awaitable_function_list): 
                if self.ConcurrencySafeContext(self.node_stack):
                    self.awaitable_nodes.append(node)
       return node

    def visit_Name2(self, node):
        if node.id in self.awaitable_function_list and isinstance(node.ctx, ast.Store):
            # if a variable name is modified that has the same name as an awaitable function, remove that function  from the list
            self.awaitable_function_list.remove(node.id)
        return node
      
def Scan(tree, awaitable_functionlist, parent=None):
    analyzer = AwaitableNodesAnalyzer(awaitable_functionlist, parent)
    analyzer.visit(tree)
    return analyzer

