import ast
from re import S
from xml.dom import Node

from . import Util
from . import scope_analyzer

class Rewriter(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        super().__init__(copy) 
        self.unique_name_id = 0
    
    def visit_Call(self, node):
        if node not in self.critical_nodes:
            return self.generic_visit(node)

        new_args=[]
        for arg in node.args:
            new_args.append(self.place(arg, self.visit(arg)))

        new_keywords=[]
        for kw in node.keywords:
            new_kw_arg = self.visit(kw.value)
            new_place = self.place(kw.value, new_kw_arg)
            new_kw = ast.keyword(arg=kw.arg, value=new_place)
            new_keywords.append(new_kw)
            
        function_call = ast.Attribute(
            value=ast.Name(id='orchestrator', ctx=ast.Load()), 
            attr=node.func.id,
            ctx=ast.Load()
        )

        call =  ast.Call(func=function_call, args=new_args, keywords=new_keywords)

        groupname = self.current_node_lookup.concurrency_group.name
        unique_name = self.MakeUniqueName()
        assign = ast.Assign(targets=[self.MakeStoreName(unique_name)], value = call)
        if groupname not in self.concurrency_start_code:
            self.concurrency_start_code[groupname]=[]
        self.concurrency_start_code[groupname].append(assign)
        if groupname not in self.concurrency_start_nonlocals:
            self.concurrency_start_nonlocals[groupname]={}
        self.concurrency_start_nonlocals[groupname].add(unique_name)
        
        return ast.Await(value = self.MakeLoadName(unique_name))
            
    def place(self, orig, node):
        if isinstance(node, ast.Name):
            return node
        if isinstance(node, ast.Constant):
            return node
        nodec = self.nodelookup[orig]
        groupname = nodec.concurrency_group.name
        unique_name = self.MakeUniqueName()
        assign = ast.Assign(targets=[self.MakeStoreName(unique_name)], value = node)
        self.concurrency_group_code[groupname].append(assign)
        self.add_nonlocal(groupname, node.id)


        return self.MakeLoadName(unique_name)
    
    def visit_Name2(self, node):
        groupname = self.current_node_lookup.concurrency_group.name
        self.add_nonlocal(groupname, node.id)
    
    def add_nonlocal(self, groupname, id):
        if groupname not in self.concurrency_group_nonlocals:
            self.concurrency_group_nonlocals[groupname]={}
        self.concurrency_group_nonlocals[groupname].add(id)
        self.allnonlocals.add(id)
        
    def visit_Module(self, node):
        self.concurrency_group_code = {}
        self.concurrency_start_code = {}
        self.concurrency_group_nonlocals = {}
        self.concurrency_start_nonlocals = {}
        self.allnonlocals = {}
        for statement in node.body:
            statement_node_lookup = self.nodelookup[statement]
            self.statement_group = statement_node_lookup.concurrency_group
            statement_group_name = self.statement_group.name
            if statement_group_name not in self.concurrency_group_code:
                self.concurrency_group_code[statement_group_name]=[]
            new_statement = self.visit(statement)
            self.concurrency_group_code[statement_group_name].append(new_statement)

        for groupname in self.concurrency_group_nonlocals:
            self.concurrency_group_code[groupname]=self.prependGlobals(self.concurrency_group_code[groupname], self.concurrency_group_nonlocal)
                                 
        for groupname in self.concurrency_start_nonlocals:
            self.concurrency_start_code[groupname]=self.prependGlobals(self.concurrency_start_code[groupname], self.concurrency_start_nonlocal)
                                 
        self.concurrency_group_nonlocals = {}

        new_body_statements = []
        final_statements = []
        for group_name in self.concurrency_group_code.keys():
            if group_name=="GF":
                final_statements = self.concurrency_group_code[group_name]
            else:
                function_def=self.MakeFunctionDef(          
                    '_concurrent_'+group_name,
                    self.concurrency_group_code[group_name])

                new_body_statements.append(function_def)
            
            if group_name in self.concurrency_start_code:
                function_def=self.MakeFunctionDef(          
                    '_concurrent_start_'+group_name,
                    self.concurrency_start_code[group_name])

                new_body_statements.append(function_def)
                
        for symbol in self.allnonlocals:
            targets= [self.MakeStoreName(symbol)]
            value=ast.NameConstant(value=None)
            statement = ast.Assign(targets=tafgets, value=value)
            new_body_statements.append(statement)

        for statement in final_statements:
            if isinstance(statement, ast.Return):
                if statement.value:
                    callnode = ast.Call(func=self.MakeLoadName("Return"), args=[statement.value], keywords=[])
                    new_body_statements.append(callnode) 
            else:
                new_body_statements.append(statement)
        
        return ast.Module(body=new_body_statements, type_ignores=node.type_ignores)


    def prependGlobals(self, list, symbols):
        new_list = []
        for symbol in self.concurrency_group_nonlocals[groupname]:
            new_list.append(ast.Global(self.MakeLoadName(symbol)))
        for statement in list:
            new_list.append(statement)

    def MakeLoadName(self, name):
        return ast.Name(id=name, ctx=ast.Load())
            
    def MakeStoreName(self, name):
        return ast.Name(id=name, ctx=ast.Store())
            
    def MakeCall(self, name, args):
        return ast.Call(func=self.MakeLoadName(name), args=args, keywords=[])
            
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
    
    def MakeUniqueName(self):
        self.unique_name_id+=1
        return "__"+str(self.unique_name_id)

        
def Scan(tree, parent=None):
    analyzer = Rewriter(parent)
    return analyzer.visit(tree)

