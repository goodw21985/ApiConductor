import ast
import sys

from ast_transform import scope_analyzer
from ast_transform import common
from ast_transform import astor_fork


class Rewriter(scope_analyzer.ScopeAnalyzer):
    ORCHESTRATOR = "orchestrator"
    ORCHESTRATORMODULE = "orchestrator"
    ORCHESTRATORCLASS = "Orchestrator"
    RETURNFUNCTION = "Return"
    PROGRAMFUNCTION = "_program"
    FUNCTIONPREFIX = "_concurrent_"
    RETURN_VALUE_NAME = "_return_value"
    FUNCTIONDISPATCH = "_dispatch"
    RESULTNAME = "Result"
    TASKFUNCTION = "Task"
    TASKCLASS = "Task"
    CALLID = "_id"

    def __init__(self, copy):
        self.pass_name = "rewriter"
        super().__init__(copy)
        self.unique_name_id = 0
        self.unique_names = {}
        self.dag = {}
        for group in self.concurrency_groups:
            self.dag[self.FUNCTIONPREFIX+group.name]=[]

    def visit_Return(self, node):
        # _return_value = x
        groupname = self.current_node_lookup.assigned_concurrency_group.name
        self.concurrency_group_nonlocals[groupname].add(self.RETURN_VALUE_NAME)
        val = self.visit(node.value)

        return ast.Assign(
            targets=[self.MakeStoreName(self.RETURN_VALUE_NAME)], value=val
        )

    def visit_Call(self, node):
        if node not in self.critical_nodes:
            return self.generic_visit(node)

        group = self.current_node_lookup.assigned_concurrency_group

        # => orchestrator.search_email(q, 0, id="_C0")
        call_id = "_" + self.critical_node_names[node]
        new_args = []
        for arg in node.args:
            new_args.append(self.place(arg, self.visit(arg)))

        new_keywords = []
        for kw in node.keywords:
            new_kw_arg = self.visit(kw.value)
            new_place = self.place(kw.value, new_kw_arg)
            new_kw = ast.keyword(arg=kw.arg, value=new_place)
            new_keywords.append(new_kw)

        new_keyword = ast.keyword(
            arg=self.CALLID, 
            value=self.MakeString(call_id))
        
        new_keywords.append(new_keyword)

        function_call = ast.Attribute(
            value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
            attr=node.func.id,
            ctx=ast.Load(),
        )

        call = ast.Call(func=function_call, args=new_args, keywords=new_keywords)

        if self.config.use_async:
            call = self.MakeTask(call)

        # => _C0 = asyncio.create_task(orchestrator.search_email(q, 0))

        #group = self.critical_node_to_group[node]
        groupname = group.name
        assign = ast.Assign(targets=[self.MakeStoreName(call_id)], value=call)
        self.concurrency_start_code[groupname].append(assign)
        self.add_nonlocal(groupname, call_id)
        self.allnonlocals.add(call_id)

        triggered = group.triggers[0]

        delegate = self.FUNCTIONPREFIX + triggered.name
        if call_id not in self.dag[delegate]:
            self.dag[delegate].append(call_id)
            
        # add nonlocals data
        self.add_nonlocal(groupname, call_id)
        for new_arg in new_args:
            if isinstance(new_arg, ast.Name):
                self.concurrency_group_nonlocals[groupname].add(new_arg.id)
        for new_kw in new_keywords:
            if isinstance(new_kw.value, ast.Name):
                self.concurrency_group_nonlocals[groupname].add(new_kw.value.id)

        parent_group = self.node_lookup[self.node_stack[-2]].assigned_concurrency_group.name
        self.add_nonlocal(parent_group, call_id)
        return self.DoWait(self.MakeLoadName(call_id))

    def MakeString(self, string):
        if sys.version_info >= (3, 9):
            return ast.Constant(value=string)
        else:
            return ast.Str(s=string)
            
        
        
    def place(self, orig, node):
        if isinstance(node, ast.Name):
            return node
        if sys.version_info >= (3, 9):
            if isinstance(node, ast.Constant):
                return node
        else:
            if isinstance(node, ast.Num):
                return node
            if isinstance(node, ast.Str):
                return node
            if isinstance(node, ast.Bytes):
                return node
            if isinstance(node, ast.Ellipsis):
                return node
            if isinstance(node, ast.NameConstant):
                return node
        nodec = self.node_lookup[orig]
        groupname = nodec.assigned_concurrency_group.name
        unique_name = self.MakeUniqueName()
        assign = ast.Assign(targets=[self.MakeStoreName(unique_name)], value=node)
        self.concurrency_group_code[groupname].append(assign)
        self.add_nonlocal(groupname, unique_name)

        return self.MakeLoadName(unique_name)

    def visit_Name2(self, node):
        symbol = self.current_node_lookup.symbol
        if symbol.usage_by_type(common.SymbolTableEntry.ATTR_WRITE):
            groupname = self.current_node_lookup.assigned_concurrency_group.name
            self.add_nonlocal(groupname, node.id)
        return node

    def add_nonlocal(self, groupname, id):
        self.concurrency_group_nonlocals[groupname].add(id)
        self.allnonlocals.add(id)

    def MakeDictionary(self, dict):
        key_nodes = []
        value_nodes = []
        for key in dict.keys():
            key_nodes.append(ast.Name(id = key, ctx=ast.Load()))
            inList=dict[key]
            if len(inList)==0:
                value_nodes.append(ast.List(elts=[], ctx=ast.Load()))
            else:
                list_elements = [self.MakeString(item) for item in inList]
                value_nodes.append(ast.List(elts=list_elements, ctx=ast.Load()))
        return ast.Dict(keys=key_nodes, values=value_nodes)
        
    def visit_Module(self, node):
        self.concurrency_group_code = {}
        self.concurrency_start_code = {}
        self.concurrency_group_nonlocals = {}
        for group in self.concurrency_groups:
            self.concurrency_group_code[group.name]=[]
            self.concurrency_start_code[group.name]=[]
            self.concurrency_group_nonlocals[group.name]=set([])

        self.allnonlocals = set([self.RETURN_VALUE_NAME])

        if self.concurrency_groups[0] == None:
            raise ValueError("165")
        statement_group_name = self.concurrency_groups[0].name
        for statement in node.body:
            if statement in self.node_lookup:
                # if we cannot find the statement, it is probably an
                # unreferenced statement..  perhaps for logging?
                # add to previous group
                statement_node_lookup = self.node_lookup[statement]
                self.statement_group = statement_node_lookup.assigned_concurrency_group
                if self.statement_group == None:
                    raise ValueError("174")
                statement_group_name = self.statement_group.name
            new_statement = self.visit(statement)
            self.concurrency_group_code[statement_group_name].append(new_statement)

        for groupname in self.concurrency_group_code.keys():
            if groupname in self.concurrency_start_code:
                self.concurrency_group_code[groupname] += self.concurrency_start_code[
                    groupname
                ]

        for groupname in self.concurrency_group_nonlocals:
            self.concurrency_group_code[groupname] = self.prependNonlocals(
                self.concurrency_group_code[groupname],
                self.concurrency_group_nonlocals[groupname],
            )

        new_body_statements = []

        # =>  __1, __2 = None
        targets = []
        targetlines = [targets]
        char_count_in_line = 0
        for symbol in sorted(self.allnonlocals):
            char_count_in_line+=len(symbol)+4
            if char_count_in_line>700:
                targets=[]
                targetlines.append(targets)
                char_count_in_line=0;
            targets.append(self.MakeStoreName(symbol))
        for targets in targetlines:
            value = ast.Constant(value=None)
            statement = ast.Assign(targets=targets, value=value)
            new_body_statements.append(statement)

        # => async def _concurrent_G0()
        for group_name in self.concurrency_group_code.keys():
            function_def = self.MakeFunctionDef(
                self.FUNCTIONPREFIX + group_name,
                self.concurrency_group_code[group_name],
                isAsync=self.config.use_async,
            )

            new_body_statements.append(function_def)

        # => orchestrator.dispatch(_concurrent_G0)
        argument = self.MakeDictionary(self.dag)

        c = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.FUNCTIONDISPATCH,
                ctx=ast.Load(),
            ),
            args=[argument],
            keywords=[],
        )

        new_body_statements.append(ast.Expr(c))

        # => return _return_value
        new_body_statements.append(
            ast.Return(self.MakeLoadName(self.RETURN_VALUE_NAME))
        )

        # => def _program(orchestrator):
        arguments = ast.arguments(
            args=[ast.arg(arg=self.ORCHESTRATOR, annotation=None)],  # List of arguments
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[]  # No default values
        )

        program = function_def = self.MakeFunctionDef(
            self.PROGRAMFUNCTION, new_body_statements, inargs=arguments
        )

        # => orchestrator.Return(_program(orchestrator))
        args1=[ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load())]
        call_program = ast.Call(
            func=ast.Name(self.PROGRAMFUNCTION, ctx=ast.Load()), args=args1, keywords=[]
        )
        call_return = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.RETURNFUNCTION,
                ctx=ast.Load(),
            ),
            args=[call_program],  # Argument list
            keywords=[],  # No keyword arguments
        )

        # => orchestrator = orchestrator.Orchestrator()
        intantiated_class = ast.Name(id=self.ORCHESTRATOR, ctx=ast.Store())

        instantiation = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATORMODULE, ctx=ast.Load()),
                attr=self.ORCHESTRATORCLASS,
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[],
        )

        # => import orchestrator
        # => import asyncio
        # => orchestrator = orchestrator.Orchestrator()
        # => def _program():
        # => orchestrator.Return(_program())
        module_statements = [
            ast.Import(names=[ast.alias(name=self.ORCHESTRATORMODULE, asname=None)]),
            ast.Assign(targets=[intantiated_class], value=instantiation),
            program,
            ast.Expr(call_return),
        ]

        if sys.version_info >= (3, 8):
            return ast.Module(body=module_statements, type_ignores=node.type_ignores)
        else:
            return ast.Module(body=module_statements)

    def prependNonlocals(self, list, symbols):
        new_list = []
        new_list.append(ast.Nonlocal(names=sorted(symbols)))
        for statement in list:
            new_list.append(statement)
        return new_list

    def MakeLoadName(self, name):
        name = ast.Name(id=name, ctx=ast.Load())
        return name

    def MakeStoreName(self, name):
        return ast.Name(id=name, ctx=ast.Store())

    def DoWait(self, node):
        if self.config.use_async:
            return ast.Await(value=node)
        else:
            return ast.Attribute(value=node, attr=self.RESULTNAME, ctx=ast.Load())
    
    def MakeFunctionDef(self, name, body, isAsync=False, inargs=None):
        args = inargs or ast.arguments(
            args=[],           
            vararg=None,       
            kwarg=None,        
            defaults=[],       
            kw_defaults=[],
            kwonlyargs=[]
        )

        if isAsync:
            function_def = ast.AsyncFunctionDef(
                name=name,
                args=args,
                body=body or [ast.Pass()],
                decorator_list=[],
                returns=None,
                type_comment=None,
            )
        else:
            function_def = ast.FunctionDef(
                name=name,
                args=args,
                body=body or [ast.Pass()],
                decorator_list=[],
                returns=None,
            )

        return function_def
        
    def MakeTask(self, node):
        if self.config.use_async:
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="asyncio", ctx=ast.Load()),
                    attr="create_task",
                    ctx=ast.Load(),
                ),
                args=[node],
                keywords=[],
            )
        else:
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(self.ORCHESTRATOR, ctx=ast.Load()),
                    attr=self.TASKFUNCTION,
                    ctx=ast.Load(),
                ),
                args=[node],
                keywords=[],
            )

    def MakeRun(self, node):
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="asyncio", ctx=ast.Load()), attr="run", ctx=ast.Load()
            ),
            args=[node],
            keywords=[],
        )

    def MakeUniqueName(self, node=None):
        self.unique_name_id += 1
        name = "_" + str(self.unique_name_id)
        if node != None:
            self.unique_names[node] = name
        return name


def Scan(tree, parent=None):
    analyzer = Rewriter(parent)
    return analyzer.visit(tree)
