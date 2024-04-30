import ast

from . import scope_analyzer

class Rewriter(scope_analyzer.ScopeAnalyzer):
    orchestrator = "orchestrator"
    orchestratorModule = "orchestrator"
    orchestratorClass = "Orchestrator"
    returnFunction = "Return"
    programFunction = "_program"
    functionPrefix = "_concurrent_"
    completionPrefix = "_completion"
    functionAddTask = '_add_task'
    return_value_name = '_return_value'
    functionDispatch = '_dispatch'
    setPrefix = '_await_set_'
    def __init__(self, copy):
        super().__init__(copy) 
        self.unique_name_id = 0
        self.unique_names = {}
        self.await_sets={}

    def visit_Return(self, node):
        # _return_value = x
        groupname = self.current_node_lookup.concurrency_group.name
        self.concurrency_group_nonlocals[groupname].add(self.return_value_name)
        val = self.generic_visit(node.value)
        return ast.Assign(targets=[self.MakeStoreName(self.return_value_name)], value = val)
  
    def visit_Call(self, node):
        if node not in self.critical_nodes:
            return self.generic_visit(node)

        # => orchestrator.search_email(q, 0)
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
            value=ast.Name(id=self.orchestrator, ctx=ast.Load()), 
            attr=node.func.id,
            ctx=ast.Load()
        )

        call1 =  ast.Call(func=function_call, args=new_args, keywords=new_keywords)
        
        call = self.MakeTask(call1)

        # => _1 = asyncio.create_task(orchestrator.search_email(q, 0))
        
        group = self.current_node_lookup.concurrency_group
        groupname = group.name
        unique_name = self.MakeUniqueName(node)
        assign = ast.Assign(targets=[self.MakeStoreName(unique_name)], value = call)
        if groupname not in self.concurrency_start_code:
            self.concurrency_start_code[groupname]=[]
        self.concurrency_start_code[groupname].append(assign)
        self.concurrency_group_nonlocals[groupname].add(unique_name)
        self.allnonlocals.add(unique_name)
       
        triggered = group.triggers[0]
        
        if len(triggered.node_dependencies)==1:
            delegate = self.functionPrefix+triggered.name
        else:
            delegate = self.completionPrefix+unique_name
       
        # => orchestrator.add_task(_1, _completion__1)
        add_task_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.orchestrator, ctx=ast.Load()), 
                attr=self.functionAddTask, 
                ctx=ast.Load()
            ),
            args=[
                ast.Name(id=unique_name, ctx=ast.Load()),  # First argument '__1'
                ast.Name(id=delegate, ctx=ast.Load())  # Second argument '_completion__1'
            ],
            keywords=[]  # No keyword arguments
        )
        
        self.concurrency_start_code[groupname].append(ast.Expr(add_task_call))

        if delegate.startswith(self.completionPrefix):
            self.concurrency_completion_code[unique_name] = self.CompletionCode(node, triggered)

        # add nonlocals data
        if groupname not in self.concurrency_group_nonlocals:
            self.concurrency_group_nonlocals[groupname]=set([])

        self.concurrency_group_nonlocals[groupname].add(unique_name)
        for new_arg in new_args:
            if isinstance(new_arg, ast.Name):
                self.concurrency_group_nonlocals[groupname].add(new_arg.id)
        for new_kw in new_keywords:
            if isinstance(new_kw.value, ast.Name):
                self.concurrency_group_nonlocals[groupname].add(new_kw.value.id)
          
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
        symbol = self.current_node_lookup.symbol
        if symbol.write:
            # system symbol does not require nonlocal
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
        self.concurrency_completion_code = {}
        self.concurrency_group_nonlocals = {}
        self.allnonlocals = set([self.return_value_name])
        
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

        for groupname in self.concurrency_group_code.keys():
            if groupname in self.concurrency_start_code:
                self.concurrency_group_code[groupname] += self.concurrency_start_code[groupname]
                
        for groupname in self.concurrency_group_nonlocals:
            self.concurrency_group_code[groupname]=self.prependNonlocals(self.concurrency_group_code[groupname], self.concurrency_group_nonlocals[groupname])
                                 
        self.concurrency_group_nonlocals = {}
        new_body_statements = []
        
        for group_name in self.await_sets.keys():
            set_name = self.setPrefix + group_name
            string_nodes = [ast.Constant(value=s) for s in self.await_sets[group_name]]
            assign_node = ast.Assign(
                targets=[ast.Name(id=set_name, ctx=ast.Store())], 
                value=ast.Set(elts=string_nodes)
            )
            
            new_body_statements.append(assign_node)

        # =>  __1 = None
        for symbol in sorted(self.allnonlocals):
            targets= [self.MakeStoreName(symbol)]
            value=ast.Constant(value=None)
            statement = ast.Assign(targets=targets, value=value)
            new_body_statements.append(statement)

        # => async def _concurrent_G0()
        for group_name in self.concurrency_group_code.keys():
            function_def=self.MakeFunctionDef(          
                self.functionPrefix+group_name,
                self.concurrency_group_code[group_name],
                isAsync=True)

            new_body_statements.append(function_def)
                
        # => async def _completion__0()
        for orc_call in self.concurrency_completion_code.keys():
            function_def=self.MakeFunctionDef(          
                self.completionPrefix+orc_call,
                self.concurrency_completion_code[orc_call],
                isAsync = True)

            new_body_statements.append(function_def)

        # => orchestrator.dispatch(_concurrent_G0)
        new_body_statements.append(ast.Expr(ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.orchestrator, ctx=ast.Load()), 
                attr=self.functionDispatch, 
                ctx=ast.Load()
            ),
            args=[ast.Name(self.functionPrefix+self.concurrency_groups[0].name)],
            keywords=[])))

        # => return _return_value
        new_body_statements.append(ast.Return(self.MakeLoadName(self.return_value_name)))

        # => def _program():
        program = function_def=self.MakeFunctionDef(          
                    self.programFunction,
                    new_body_statements)

        # => orchestrator.Return(_program())
        call_program = ast.Call(func = ast.Name(self.programFunction),args=[],keywords=[])
        call_return = ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id=self.orchestrator, ctx=ast.Load()),  
                                attr=self.returnFunction,  
                                ctx=ast.Load()  
                            ),
                            args=[call_program],  # Argument list
                            keywords=[]  # No keyword arguments
                        )
        
        # => orchestrator = orchestrator.Orchestrator()
        intantiated_class = ast.Name(id=self.orchestrator, ctx=ast.Store())
        
        instantiation = ast.Call(
            func=ast.Attribute(value=ast.Name(id=self.orchestratorModule, ctx=ast.Load()), attr=self.orchestratorClass, ctx=ast.Load()),
            args=[],
            keywords=[],
            starargs=None,
            kwargs=None
        )

        # => import orchestrator
        # => import asyncio
        # => orchestrator = orchestrator.Orchestrator()
        # => def _program():
        # => orchestrator.Return(_program())
        module_statements = [
            ast.Import(names=[ast.alias(name=self.orchestratorModule, asname=None)]),
            ast.Import(names=[ast.alias(name="asyncio", asname=None)]),
            ast.Assign(targets=[intantiated_class], value=instantiation),
            program,
            ast.Expr(call_return)
            ]

        return ast.Module(body=module_statements, type_ignores=node.type_ignores)

    def CompletionCode(self, node, triggered):
        uniqueName = self.unique_names[node]
        if triggered.name not in self.await_sets:
            self.await_sets[triggered.name]=[]
        self.await_sets[triggered.name].append(uniqueName)
        statements = []

        # nonlocal _await_set_G2
        setname = self.setPrefix+triggered.name       
        statements.append(ast.Nonlocal([setname]))
        
        # _await_set_G2.remove("__1")
        statements.append(ast.Expr(value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=setname, ctx=ast.Load()),
                attr='remove',
                ctx=ast.Load()
            ),
            args=[
                ast.Constant(value=uniqueName)
            ],
            keywords=[]
        )))

        # if not _await_set_G1 : await _concurrent_G1() 
        statements.append(ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Name(id=setname, ctx=ast.Load())
            ),
            body=[
                ast.Expr(
                    value=ast.Await(ast.Call(
                        func=ast.Name(id=self.functionPrefix+triggered.name, ctx=ast.Load()),
                        args=[],
                        keywords=[]
                    ))
                )
            ],
            orelse=[]
        ))
        
        return statements
    
    def prependNonlocals(self, list, symbols):
        new_list = []
        new_list.append(ast.Nonlocal(names=sorted(symbols)))
        for statement in list:
            new_list.append(statement)
        return new_list

    def MakeLoadName(self, name):
        name= ast.Name(id=name, ctx=ast.Load())
        return name
            
    def MakeStoreName(self, name):
        return ast.Name(id=name, ctx=ast.Store())
            
    
    def MakeFunctionDef(self, name, body, isAsync=False):
        args = ast.arguments(                
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
            varargs=None,
            kwarg=None
        )

        if isAsync:
            function_def = ast.AsyncFunctionDef(
                name=name,
                args=args,
                body=body or [ast.Pass()],
                decorator_list=[],
                returns=None,
                type_comment=None
            )
        else:
            function_def = ast.FunctionDef(
                name=name,
                args=args,
                body=body or [ast.Pass()],
                decorator_list=[],
                returns=None,
                type_comment=None
            )
        
        return function_def
    
    def MakeTask(self, node):
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='asyncio', ctx=ast.Load()),
                attr='create_task',
                ctx=ast.Load()
            ),
            args=[node],
            keywords=[]
        )
    
    def MakeRun(self, node):
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='asyncio', ctx=ast.Load()),
                attr='run',
                ctx=ast.Load()
            ),
            args=[node],
            keywords=[]
        )

    def MakeUniqueName(self, node=None):
        self.unique_name_id+=1
        name = "_"+str(self.unique_name_id)
        if node != None:
            self.unique_names[node]=name
        return name

        
def Scan(tree, parent=None):
    analyzer = Rewriter(parent)
    return analyzer.visit(tree)

