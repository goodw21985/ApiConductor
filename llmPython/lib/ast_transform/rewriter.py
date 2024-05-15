import ast
import sys

from ast_transform import scope_analyzer
from ast_transform import common
from ast_transform import astor_fork

# this class rewrites the code by creating a function for
# each concurrency group, and creating a dag that references 
# these functions.  In the main program function that is 
# created, a single call is made to a dispatcher with the dag
#
# the original code is walked and sections of that code are
# placed in one (or more) concurrency group functions.
#
# concurrency group functions do not use parameters, and share
# all variables with each other and the program via the python nonlocal statement
#
# three dictionaries are used to build the concurrency groups code, 
# each keyed off the concurrency group:
# concurrency_start_code: code that starts an async critical node
# concurrency_group_code: lines of code for the body of the function
# concurrency_group_nonlocals: all shared variables used by this function

class Rewriter(scope_analyzer.ScopeAnalyzer):
    ORCHESTRATOR = "orchestrator"
    ORCHESTRATORMODULE = "orchestrator"
    ORCHESTRATORCLASS = "Orchestrator"
    RETURNFUNCTION = "Return"
    PROGRAMFUNCTION = "_program"
    FUNCTIONPREFIX = "_concurrent_"
    RETURN_VALUE_NAME = "_return_value"
    FUNCTIONDISPATCH = "_dispatch"
    FUNCTIONCOMPLETE = "_complete"
    FUNCTIONCOMPLETECOMP = "_complete_comp"
    FUNCTIONCREATEID = "_create_id"
    FUNCTIONCREATETASK = '_create_task'
    FUNCTIONWAIT = "_wait"
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
        self.dag_aggregate_groups = set([])
        self.comp_groups = {}
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

    def visit_SetComp2(self, node):
        generators = [self.visit(g) for g in node.generators]
        call = self.visit(node.elt)
        if node not in self.critical_nodes: 
            return ast.SetComp(elt = call, generators=generators)
        
        call_id = "_" + self.critical_node_names[node]
        agg_group_id = "G_" + self.critical_node_names[node]
        call_id_comp = "_comp_" + self.critical_node_names[node]
        group = self.current_node_lookup.assigned_concurrency_group
        # assign call to call_id variable
        groupname = group.name
        list_comp = ast.ListComp(elt=call, generators=generators)
        assign = ast.Assign(targets=[self.MakeStoreName(call_id_comp)], value=list_comp)
        self.concurrency_start_code[groupname].append((node,assign))
        self.concurrency_start_code[groupname].append((node,self.comp_completion(call_id, agg_group_id,call_id_comp)))
        
        self.add_nonlocal(groupname, call_id)
        self.allnonlocals.add(call_id_comp)
        self.allnonlocals.add(call_id)

        parent_group = self.node_lookup[self.node_stack[-2]].assigned_concurrency_group.name
        self.add_nonlocal(parent_group, call_id_comp)

        self.add_to_dag(group, call_id)
        self.add_to_dag_simple(agg_group_id, call_id_comp)
        
        # =>  _C0.Result = {item.Result for item in _comp_C0}
        self.concurrency_group_code[agg_group_id] = [self.create_set_comp(call_id,call_id_comp),self.aggregation_completion(call_id)]
        self.concurrency_start_code[agg_group_id] = []
        self.concurrency_group_nonlocals[agg_group_id] = [call_id,call_id_comp]
        
        self.comp_groups[call_id] = node
        return self.DoWait(self.MakeLoadName(call_id))
        
    def visit_Call_For_Comprehension(self, call_node, comp_node):
        call_id = "_" + self.critical_node_names[comp_node]
        
        # {search_email(item) for item in range(10) if item % 2 == 0}
        st = astor_fork.to_source(comp_node)
        comp_args =[g.target.id for g in comp_node.generators]
        new_args = []
        for arg in call_node.args:
            if isinstance(arg, ast.Name) and arg.id in comp_args:
                new_args.append(arg)
            else:
                new_args.append(self.place(arg, self.visit(arg)))

        new_keywords = []
        for kw in call_node.keywords:
            if isinstance(kw.value, ast.Name) and kw.value.id in comp_args:
                new_kw = ast.keyword(arg=kw.arg, value=kw.value)
                new_keywords.append(new_kw)
            else:
                new_kw_arg = self.visit(kw.value)
                new_place = self.place(kw.value, new_kw_arg)
                new_kw = ast.keyword(arg=kw.arg, value=new_place)
                new_keywords.append(new_kw)

        new_keyword = ast.keyword(
            arg=self.CALLID, 
            value=self.create_runtime_id(call_id))
        
        new_keywords.append(new_keyword)

        function_call = ast.Attribute(
            value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
            attr=call_node.func.id,
            ctx=ast.Load(),
        )

        call = ast.Call(func=function_call, args=new_args, keywords=new_keywords)
        return call
    
    def add_to_dag_simple(self, group_id, call_id):
        delegate = self.FUNCTIONPREFIX + group_id
        if delegate not in self.dag:
            self.dag[delegate]=[]
        if call_id not in self.dag[delegate]:
                self.dag[delegate].append(call_id)

    def add_to_dag(self, group, call_id):
        is_aggregate=False
        for triggered in group.triggers:        
            delegate = self.FUNCTIONPREFIX + triggered.name
            if triggered.is_aggregation_group:
                is_aggregate=True
                self.dag_aggregate_groups.add(delegate)
                for retriggered in triggered.triggers:
                    redelegate = self.FUNCTIONPREFIX +retriggered.name
                    if triggered.name not in self.dag[redelegate]:
                        self.dag[redelegate].append(triggered.name)
                        
        if not is_aggregate:
            for triggered in group.triggers:        
                delegate = self.FUNCTIONPREFIX + triggered.name
                if call_id not in self.dag[delegate]:
                    self.dag[delegate].append(call_id)
            
             

    def visit_Call(self, node):
        if self.node_stack[-2] in self.critical_nodes:
            parent = self.node_stack[-2]
            if isinstance(parent, ast.SetComp) or isinstance(parent,ast.ListComp) or isinstance(parent, ast.DictComp):
                return self.visit_Call_For_Comprehension(node, parent)
        
        if node not in self.critical_nodes: # and not parent_critical:
            return self.generic_visit(node)

        group = self.current_node_lookup.assigned_concurrency_group

        # => orchestrator.search_email(q, 0, id="_C0")
        call_id = "_" + self.critical_node_names[node]
        new_args = []

        # for critical nodes we found unsafe, we still need to rewrap them, but not 
        # place construction across concurrency groups, and also immediatly call _wait()
        if node in self.non_concurrent_critical_nodes:
            for arg in node.args:
                new_args.append(self.visit(arg))
                
            new_keywords = []
            for kw in node.keywords:
                new_kw = ast.keyword(arg=kw.arg, value=self.visit(kw.value))
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
            call= self.call_wait(call, call_id)
            self.add_nonlocal(group.name, call_id)
            return call

        # place arguments in separate concurrency groups, and add 'id' parameter
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


        # assign call to call_id variable
        groupname = group.name
        assign = ast.Assign(targets=[self.MakeStoreName(call_id)], value=call)
        self.concurrency_start_code[groupname].append((node,assign))
        self.add_nonlocal(groupname, call_id)
        self.allnonlocals.add(call_id)

        if node in self.aggregated:
            agg_group = self.aggregated[node]
            delegate = self.FUNCTIONPREFIX + agg_group.name
            # embed the list within a list that only contains the outer list
            # as a flag to the dispatcher that this is OR list not and AND list        
            if len(self.dag[delegate])==0:
                self.dag[delegate].append([])
            if call_id not in self.dag[delegate][0]:
                self.dag[delegate][0].append(call_id)

        self.add_to_dag(group, call_id)

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
        self.add_concurrency_group_code(groupname, assign)
        self.add_nonlocal(groupname, unique_name)

        return self.MakeLoadName(unique_name)

    def visit_Assign(self, node):
        result = self.generic_visit(node)

        # get rid of assignments of None to if group variable assignements
        if common.is_constant(node.value) and node.value.value==None:
            targets=[]
            targets_changed = False
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in self.critical_nodes_if_groups.values():
                    targets.append(ast.Name(id='_', ctx = target.ctx))
                    targets_changed = True
                else:
                    targets.append(target)

            if targets_changed:
                return ast.Assign(targets = targets, value=node.value)
                        
                        
        return result

    def visit_AugAssign(self, node):
        result = self.generic_visit(node)
        return result
    
    def visit_Name2(self, node):
        symbol = self.current_node_lookup.symbol
        if symbol.usage_by_types([common.SymbolTableEntry.ATTR_WRITE]):
            groupname = self.current_node_lookup.assigned_concurrency_group.name
            self.add_nonlocal(groupname, node.id)
        return node

    def add_nonlocal(self, groupname, id):
        self.concurrency_group_nonlocals[groupname].add(id)
        self.allnonlocals.add(id)

    # sort for consistent source code for testing to be simpler
    def SortDictionary(self, dict):
        keys = []
        for key in dict.keys():
            keys.append(key)
        keys=sorted(keys)
        result = {}
        for key in keys:
            val = dict[key]
            if len(val)==0:
                result[key]=val
            elif isinstance(val[0], list):
                result[key]=[sorted(val[0])]
            else:
                result[key]=sorted(val)
                
        return result
    
    def MakeDictionary(self, dict0):
        dict = self.SortDictionary(dict0)
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

        statement_group_name = self.concurrency_groups[0].name
        for statement in node.body:
            if statement in self.node_lookup:
                # if we cannot find the statement, it is probably an
                # unreferenced statement..  perhaps for logging?
                # add to previous group
                statement_node_lookup = self.node_lookup[statement]
                self.statement_group = statement_node_lookup.assigned_concurrency_group
                statement_group_name = self.statement_group.name
            new_statement = self.visit(statement)
            self.add_concurrency_group_code(statement_group_name, new_statement)

        for group in self.concurrency_groups:
            if group.is_aggregation_group:
                self.concurrency_group_code[group.name].append(self.aggregation_completion(group.name))

        self.UncompletedAsyncIfs()        
                
        for groupname in self.concurrency_group_code.keys():
            if groupname in self.concurrency_start_code:
                
                self.concurrency_group_code[groupname] += self.BuildStartCode(self.concurrency_start_code[
                    groupname
                ])

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

        # => def _concurrent_G0()
        for group_name in self.concurrency_group_code.keys():
            function_def = self.MakeFunctionDef(
                self.FUNCTIONPREFIX + group_name,
                self.concurrency_group_code[group_name],
                isAsync=False,
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

    def add_concurrency_group_code(self, group_name, statement):
        self.concurrency_group_code[group_name].append(statement)

    def prependNonlocals(self, list, symbols):
        if not symbols:
            return list
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
        return ast.Attribute(value=node, attr=self.RESULTNAME, ctx=ast.Load())

    def UncompletedAsyncIfs(self):
        reverse_if_groups={}
        completion_id={}
        for node in self.critical_nodes_if_groups.keys():
            if_grp = self.critical_nodes_if_groups[node]
            if if_grp not in reverse_if_groups:
                reverse_if_groups[if_grp]=([],set([]))
            nodec = self.node_lookup[node]
            reverse_if_groups[if_grp][0].append(nodec.if_stack)
            reverse_if_groups[if_grp][1].add(nodec.assigned_concurrency_group)
            id = "_" + self.critical_node_names[node]
            completion_id[if_grp]=id
        for if_grp in reverse_if_groups.keys():
            concurrency_group = self.GetLatestConcurrencyGroup(reverse_if_groups[if_grp][1])
            cond = None
            if self.IfGroupsIncomplete(reverse_if_groups[if_grp][0]):
                for if_stack in reverse_if_groups[if_grp][0]:
                    cond = Rewriter.Or(cond,self.GetIfCond(if_stack))     
                
                cond = Rewriter.Not(cond)
                # => orchestrator._complete("_1")
                trigger = self.aggregation_completion(completion_id[if_grp])
                statement = ast.If(test = cond, body =[trigger], orelse=[])
                self.concurrency_group_code[concurrency_group.name].append(statement)
            

    def IfGroupsIncomplete(self, if_stacks):
        frames_report_stack = [if_stacks[0][0].if_frame,{}]
        base_type=None
        for if_stack in if_stacks:
            if base_type!= None and if_stack[0].if_frame != base_type:
                return True;
            base_type = if_stack[0].if_frame
            current = frames_report_stack
            for level in if_stack:
                current[0]=level.if_frame
                if level.block_index not in current:
                     current[1][level.block_index]=[None,{}]
                current =current[1][level.block_index]
                
        return not self.IsIfGroupsComplete(frames_report_stack)
    
    def IsIfGroupsComplete(self, report):
        frame = report[0]
        if (frame==None):
            return True
        children = report[1]
        complete_body_count = len(frame.conditions)+1
        for index in range(complete_body_count):
            if index not in children:
                return False
            report2= children[index]
            if not self.IsIfGroupsComplete(report2):
                return False
        return True
    
    def GetLatestConcurrencyGroup(self, options):
        if len(options)==1:
            return list(options)[0]
        for item in options:
            if self.GetLatestConcurrencyGroupFollow(item, item, options):
                return item
        raise ValueError

    def GetLatestConcurrencyGroupFollow(self, orig, cur, options):
        if orig != cur and cur in options:
            return False
        for next in cur.triggers:
            if not self.GetLatestConcurrencyGroupFollow(orig,next, options):
                return False
        return True

    def BuildStartCode(self, start_list):
        statements = []
        # statements need to be grouped under if trees, and there can be more than one
        ifgroups = {}
        for (node, assignStatement) in start_list:
            nodec = self.node_lookup[node]
            if not nodec.if_stack:
                statements.append(assignStatement)
            else:
                ifframe =nodec.if_stack[0].if_frame
                if ifframe not in ifgroups:
                    ifgroups[ifframe]=[]
                ifgroups[ifframe].append((node, assignStatement))    
                
        for ifgroup in ifgroups.keys():
            for statement in self.BuildStartIfTree(ifgroup, ifgroups[ifgroup]):
                statements.append(statement)

        return statements

    @staticmethod
    def Not(expr):
        return ast.UnaryOp(op=ast.Not(), operand=expr)

    @staticmethod
    def And(a, b0, invert_b=False):
        if b0==None:
            return a
        b= Rewriter.Not(b0) if invert_b else b0
        
        if a==None:
            return b
        return ast.BoolOp(op=ast.And(), values=[a, b])
    
    @staticmethod
    def Or(a, b):
        if b==None:
            return a
        
        if a==None:
            return b
        return ast.BoolOp(op=ast.Or(), values=[a, b])

    def GetIfCond(self, if_stack):
        condition_node = None
        for stack_frame in if_stack:
            block_index = stack_frame.block_index
            if_frame = stack_frame.if_frame
            expr = None
            for index in range(block_index+1):
                if index < len(if_frame.conditions):
                    condition = if_frame.conditions[index]
                    expr = Rewriter.And(expr, condition, index<block_index)
                        
            condition_node = Rewriter.And(condition_node, expr)
        return condition_node
        

    def BuildStartIfTree(self, if_group, start_list):
        statements = []
        for (node, assignStatement) in start_list:
            nodec = self.node_lookup[node]
            if_stack = nodec.if_stack
            condition_node = self.GetIfCond(if_stack)
            if_stmt = ast.If(
                test=condition_node, 
                body=[assignStatement],  
                orelse=[])
            statements.append(if_stmt)
                 
        return statements
        
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
            

    def comp_completion(self,name1, name2, name3):
        # => orchestrator._complete_comp("G_a", "_C0","_comp_C0")
        return ast.Expr(ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.FUNCTIONCOMPLETECOMP,
                ctx=ast.Load(),
            ),
            args=[self.MakeString(name1),self.MakeString(name3),self.MakeString(name3)],
            keywords=[],
        ))
    
    def aggregation_completion(self,name):
        # => orchestrator._complete("G_a")
        return ast.Expr(ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.FUNCTIONCOMPLETE,
                ctx=ast.Load(),
            ),
            args=[self.MakeString(name)],
            keywords=[],
        ))
        
    def create_runtime_id(self,name):
        # => orchestrator._create_id("_C0")
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.FUNCTIONCREATEID,
                ctx=ast.Load(),
            ),
            args=[self.MakeString(name)],
            keywords=[],
        )
        
    def call_wait(self,call, name):
        # => orchestrator._wait(orchestrator.search_email(...))
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.FUNCTIONWAIT,
                ctx=ast.Load(),
            ),
            args=[call, self.MakeString(name)],
            keywords=[],
        )
        
    def MakeTask(self, node):
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.TASKFUNCTION,
                ctx=ast.Load(),
            ),
            args=[node],
            keywords=[],
        )
    
    def create_set_comp(self, name1, name2):
        import ast

        target = ast.Name(id='_C0', ctx=ast.Store())

        generator = ast.comprehension(
            target=ast.Name(id='item', ctx=ast.Store()),
            iter=ast.Name(id=name2, ctx=ast.Load()),
            ifs=[],
            is_async=0
        )

        set_comp = ast.SetComp(
            elt=ast.Attribute(
                value=ast.Name(id='item', ctx=ast.Load()),
                attr='Result',
                ctx=ast.Load()
            ),
            generators=[generator]
        )

        call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.ORCHESTRATOR, ctx=ast.Load()),
                attr=self.FUNCTIONCREATETASK,
                ctx=ast.Load()
            ),
            args=[set_comp],
            keywords=[]
        )

        assign = ast.Assign(
            targets=[target],
            value=call
        )
        
        return assign

    def MakeUniqueName(self, node=None):
        self.unique_name_id += 1
        name = "_" + str(self.unique_name_id)
        if node != None:
            self.unique_names[node] = name
        return name


def Scan(tree, parent=None):
    analyzer = Rewriter(parent)
    return analyzer.visit(tree)
