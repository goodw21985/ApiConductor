import ast
from re import A, S
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
            self.concurrency_start_nonlocals[groupname]=set([])

        self.concurrency_start_nonlocals[groupname].add(unique_name)
        for new_arg in new_args:
            if isinstance(new_arg, ast.Name):
                self.concurrency_start_nonlocals[groupname].add(new_arg.id)
        for new_kw in new_keywords:
            if isinstance(new_kw.value, ast.Name):
                self.concurrency_start_nonlocals[groupname].add(new_kw.value.id)
          
        parent_group = self.nodelookup[self.node_stack[-2]].concurrency_group.name
        if parent_group not in self.concurrency_group_nonlocals:
            self.concurrency_group_nonlocals[parent_group]=set([])
        self.concurrency_group_nonlocals[parent_group].add(unique_name)
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
        self.add_nonlocal(groupname, unique_name)


        return self.MakeLoadName(unique_name)
    
    def visit_Name2(self, node):
        groupname = self.current_node_lookup.concurrency_group.name
        self.add_nonlocal(groupname, node.id)
        return node
    
    def add_nonlocal(self, groupname, id):
        if groupname not in self.concurrency_group_nonlocals:
            self.concurrency_group_nonlocals[groupname]=set([])
        self.concurrency_group_nonlocals[groupname].add(id)
        self.allnonlocals.add(id)
        
    def visit_Module(self, node):
        self.concurrency_group_code = {}
        self.concurrency_start_code = {}
        self.concurrency_group_nonlocals = {}
        self.concurrency_start_nonlocals = {}
        self.allnonlocals = set([])
        
        statement_group_name = self.concurrency_groups[0].name
        for statement in node.body:
            if statement in self.nodelookup:
                # if we cannot find the statement, it is probably an 
                # unreferenced statement..  perhaps for logging?
                # add to previous group
                statement_node_lookup = self.nodelookup[statement]
                self.statement_group = statement_node_lookup.concurrency_group
                statement_group_name = self.statement_group.name
            if statement_group_name not in self.concurrency_group_code:
                self.concurrency_group_code[statement_group_name]=[]
            new_statement = self.visit(statement)
            self.concurrency_group_code[statement_group_name].append(new_statement)

        for groupname in self.concurrency_group_nonlocals:
            if groupname != self.concurrency_groups[-1].name:
                self.concurrency_group_code[groupname]=self.prependGlobals(self.concurrency_group_code[groupname], self.concurrency_group_nonlocals[groupname])
                                 
        for groupname in self.concurrency_start_nonlocals:
            self.concurrency_start_code[groupname]=self.prependGlobals(self.concurrency_start_code[groupname], self.concurrency_start_nonlocals[groupname])
                                 
        self.concurrency_group_nonlocals = {}

        new_body_statements = []
        final_statements = []
        for group_name in self.concurrency_group_code.keys():
            if group_name == self.concurrency_groups[-1].name:
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
                
        for symbol in sorted(self.allnonlocals):
            targets= [self.MakeStoreName(symbol)]
            value=ast.Constant(value=None)
            statement = ast.Assign(targets=targets, value=value)
            new_body_statements.append(statement)

        if final_statements:
            for statement in final_statements:
                if isinstance(statement, ast.Return):
                    if statement.value:
                        call_node = ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="orchestrator", ctx=ast.Load()),  # Attribute value "orchestrator"
                                attr="Return",  # Attribute name "Return"
                                ctx=ast.Load()  # Load context
                            ),
                            args=[statement.value],  # Argument list
                            keywords=[]  # No keyword arguments
                        )
                        new_body_statements.append(ast.Expr(call_node)) 
                else:
                    new_body_statements.append(statement)
        
        return ast.Module(body=new_body_statements, type_ignores=node.type_ignores)


    def prependGlobals(self, list, symbols):
        new_list = []
        new_list.append(ast.Global(names=sorted(symbols)))
        for statement in list:
            new_list.append(statement)
        return new_list

    def MakeLoadName(self, name):
        name= ast.Name(id=name, ctx=ast.Load())
        return name
            
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

