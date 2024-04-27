import ast
from re import S
from xml.dom import Node

from . import Util
from . import scope_analyzer

class Rewriter(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        super().__init__(copy) 
    
    def visit_Call(self, node):
        pass

    def visit_Module(self, node):
        concurrency_group_code = {}
        concurrency_start_code = {}
        for statement in node.body:
            statement_node_lookup = self.nodelookup[statement]
            statement_group = statement_node_lookup.concurrency_group
            statement_group_name = statement_group.name
            if statement_group_name not in concurrency_group_code:
                concurrency_group_code[statement_group_name]=[]
            new_statement = self.visit(statement)
            concurrency_group_code[statement_group_name].append(new_statement)

        new_body_statements = []
        final_statements = []
        for group_name in concurrency_group_code.keys():
            if group_name=="GF":
                final_statements = concurrency_group_code[group_name]
            else:
                function_def=self.MakeFunctionDef(          
                    '_concurrent_'+group_name,
                    concurrency_group_code[group_name])

                new_body_statements.append(function_def)

        for statement in final_statements:
            if isinstance(statement, ast.Return):
                if statement.value:
                    callnode = ast.Call(func=self.MakeName("Return"), args=[statement.value], keywords=[])
                    new_body_statements.append(callnode) 
            else:
                new_body_statements.append(statement)
        
        return ast.Module(body=new_body_statements, type_ignores=node.type_ignores)

    # not in __init__ because there will be recursion within rewriter
    def setup(self):
        self.concurrency_group_code = {}
        self.curent_concurrency_group=None
        for g in self.concurrency_groups:
            self.concurrency_group_code[g] = []


    def MakeName(self, name):
        return ast.Name(id=name, ctx=ast.Load())
            
    def MakeCall(self, name, args):
        return ast.Call(func=self.MakeName(name), args=args, keywords=[])
            
    def MakeFunctionDef(self, name, body):
        args = ast.arguments(                
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
            varargs=None,
            kwarg=None
        )

        function_def = ast.FunctionDef(
            name=name,
            args=args,
            body=body,
            decorator_list=[],
            returns=None,
            type_comment=None
        )
        
        return function_def
        
def Scan(tree, parent=None):
    analyzer = Rewriter(parent)
    analyzer.setup()
    return analyzer.visit(tree)

