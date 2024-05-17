import ast
from . import scope_analyzer
from . import common

# This pass is used to create a classical pass 1 symbol table that understands when a symbol can have
# different context (local variables, parameters, class variables etc.) and creates a creates a SymbolTableEntry
# for each symbol in each context, keeping track of when a symbol is declared, read and written, etc.
# this will also keep track of when an object is modified (i.e. a.b.c=3, does modify symbol a) to keep track of immutability
# that is required for safe concurrency.
#
# This pass also assesses the safety of potential concurrency.
#
# Since we only are interested in concurrency around critical nodes (i.e. calls made from python code to an extrenal API)
# we also classify whether a critical node can be safely parallelized.  non_concurrent_critical_nodes must still be treated
# as asyncronous, however splitting code is not allowed, and we must immediately wait for results, rather than allow parallelism.

class VariablesAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, config, copy):
        self.pass_name = "variables"
        self.config = config
        super().__init__(copy)
        self.symbol_table_stack = []
        self.symbol_table_stack.append({})
        self.symbol_table = self.symbol_table_stack[-1]
        self.critical_nodes = []
        self.non_concurrent_critical_nodes = set([])
        self.critical_nodes_if_groups = {}
        self.critical_node_names = {}
        self.global_return_statement = None
        self.class_symbols_stack = []
        self.def_class_param_stack = []

        
    def visit_pre(self, node):
        if isinstance(node, ast.Compare):
            pass
        self.current_node_lookup = common.NodeCrossReference(self.current_node_stack, self.current_if_stack)
        self.node_lookup[node] = self.current_node_lookup
    
    
    def visit_Name2(self, node):
        name = node.id
        if node.id in self.config.awaitable_functions and isinstance(
            node.ctx, ast.Store
        ):
            # if a variable name is modified that has the same name as an awaitable function, remove that function  from the list
            raise ValueError(
                f"{node.id} is assigned, and is also the name of a protected function"
            )
        group = common.SymbolTableEntry.ATTR_READ
        if not self.IgnoreSymbol(node):
            if isinstance(node.ctx, ast.Store):
                q = self.IsAugAssign()
                if q == True:
                    group = common.SymbolTableEntry.ATTR_READ_WRITE
                elif q == False:
                    group = common.SymbolTableEntry.ATTR_WRITE
                else:
                    group = common.SymbolTableEntry.ATTR_AMBIGUOUS
            else:                
                last = node
                for stack_entry in self.node_stack[-2::-1]:
                    if isinstance(stack_entry, ast.Subscript):
                        last = stack_entry
                        pass
                    elif isinstance(stack_entry, ast.Attribute):
                        last = stack_entry
                        pass
                    elif isinstance(stack_entry, ast.Assign):
                        if last in stack_entry.targets:
                            group = common.SymbolTableEntry.ATTR_AMBIGUOUS
                        pass
                    elif isinstance(stack_entry, ast.AugAssign):
                        if last == stack_entry.target:
                            group = common.SymbolTableEntry.ATTR_AMBIGUOUS
                        pass
                    else:
                        break
          
            self.add_variable_reference(name, group, self.current_node_lookup)
        return node

    # looking for implicit async function usage.
    def visit_Call2(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.config.awaitable_functions:
                critical_node=node
                critical_current_node_lookup=self.current_node_lookup
                parent = self.node_stack[-2]
                
                if isinstance(parent, ast.SetComp) or isinstance(parent, ast.ListComp):
                    if parent.elt == node:
                        critical_node=parent
                        critical_current_node_lookup = self.node_lookup[parent]
                elif isinstance(parent, ast.DictComp):
                    if parent.key == node:
                        critical_node=parent
                        critical_current_node_lookup = self.node_lookup[parent]
                    elif parent.value == node:
                        critical_node=parent
                        critical_current_node_lookup = self.node_lookup[parent]
                self.critical_nodes.append(critical_node)
                self.critical_node_names[critical_node]=self.new_critical_node_name()
                if not critical_current_node_lookup.is_concurrency_safe_context():
                    self.non_concurrent_critical_nodes.add(critical_node)
        return node

    def visit_Lambda2(self, node):
        for arg in node.args.args:
            self.add_variable_reference(
                arg.arg,
                common.SymbolTableEntry.ATTR_READ,
                self.current_node_lookup,
            )
        return node

    def declare_variable(self, node):
        if isinstance(node, ast.Tuple):
            for target in node.elts:
                self.declare_variable(target)
        else:
            self.add_variable_reference(
                node,
                common.SymbolTableEntry.ATTR_DECLARED,
                self.current_node_lookup,
            )
                  
    def visit_GeneratorExp2(self, node):
        for generator in node.generators:
            self.declare_variable(generator.target)
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        return node

    def visit_DictComp2(self, node):
        for generator in node.generators:
            self.declare_variable(generator.target)
        for g in node.generators:
            self.visit(g)
        self.visit(node.key)
        self.visit(node.value)
        return node

    def visit_SetComp2(self, node):
        for generator in node.generators:
            self.declare_variable(generator.target)
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        return node

    def visit_ListComp2(self, node):
        for generator in node.generators:
            self.declare_variable(generator.target)
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        return node

    def visit_Attribute2(self, node):
        (name, isClass, isComplex) = self.GetVariableContext()
        if name==None:
            return node
        
        if isinstance(node.ctx, ast.Load):
            group = common.SymbolTableEntry.ATTR_READ
        elif isinstance(node.ctx, ast.Store):
            q = self.IsAugAssign()
            if q == True:
                group = common.SymbolTableEntry.ATTR_READ_WRITE
            elif q == False:
                group = common.SymbolTableEntry.ATTR_WRITE
            else:
                group = common.SymbolTableEntry.ATTR_AMBIGUOUS

        if isComplex:
            if group != common.SymbolTableEntry.ATTR_READ:
                group = common.SymbolTableEntry.ATTR_AMBIGUOUS

        if isClass:
            self.add_class_variable_reference(name, group, self.current_node_lookup)
        else:
            self.add_variable_reference(name, group, self.current_node_lookup)
        return node

    def push_symbol_table_stack(self, node):
        self.symbol_table = self.symbol_table[node].child
        self.symbol_table_stack.append(self.symbol_table)

    def pop_symbol_table_stack(self):
        self.symbol_table_stack.pop()
        self.symbol_table = self.symbol_table_stack[-1]


        
    def visit_arg2(self, node):
        if (
            not self.def_class_param_stack
            or self.def_class_param_stack[-1] != node.arg
        ):
            self.current_node_lookup.symbol = self.get_variable_reference(
                node.arg, self.current_node_stack
            )
        if not self.def_class_param_stack or self.def_class_param_stack[-1] != node.arg:
            self.add_variable_reference(
                node.arg,
                common.SymbolTableEntry.ATTR_DECLARED,
                self.current_node_lookup,
            )
        return node

    def visit_Global(self, node):
        for target in node.names:
            root = self.symbol_table_stack[0]
            self.Redirect(target, root)
        self.generic_visit(node)
        return node
    

    def visit_Nonlocal(self, node):
        for target in node.names:
            for ancestor in self.symbol_table_stack[:-1][::-1]:
                if not self.Redirect(target, ancestor):
                    break
        self.generic_visit(node)
        return node

    def visit_Return(self, node):
        if len(self.node_stack) == 2:
            self.global_return_statement = node
        self.generic_visit(node)
        return node

    def Redirect(self, key, value):
        if key not in self.symbol_table:
            self.symbol_table[key] = common.SymbolTableEntry()

        self.symbol_table[key].redirect = value
        if key not in value:
            value[key] = common.SymbolTableEntry()
        return value[key].redirect


    def IgnoreSymbol(self, node):
        if self.def_class_param_stack and self.def_class_param_stack[-1] == node.id:
            return True
        if isinstance(node.ctx, ast.Load):
            parent = self.current_node_stack[-2]
            if parent and isinstance(parent, ast.FunctionDef):
                return True
        return False

    def find_frame(self, key):
        latest_object_with_key = None
        for obj in reversed(self.symbol_table_stack):
            if key in obj:
                latest_object_with_key = obj
                break

            # only lambdas can implicitly get scope broadened
            if self.scope_broadened == 0:
                break
        if latest_object_with_key is not None:
            return latest_object_with_key
        else:
            return self.symbol_table_stack[-1] if self.symbol_table_stack else None

    def add_variable_reference(self, key, group, value):
        dictionary = self.find_frame(key)
        if key not in dictionary:
            dictionary[key] = common.SymbolTableEntry()
        item = dictionary[key]
        while item.redirect:
            sub = item.redirect
            if key not in sub:
                sub[key] = common.SymbolTableEntry()
            item = sub[key]
            item.notLocal = True

        item.add_usage(group,value)
        self.current_node_lookup.symbol = item

    def add_class_variable_reference(self, key, group, value):
        dictionary = self.class_symbols_stack[-1]
        if key not in dictionary:
            dictionary[key] = common.SymbolTableEntry()
        dictionary[key].add_usage(group,value)
        self.current_node_lookup.symbol = dictionary[key]

    def pop_class_symbol_stack(self):
        self.class_symbols_stack.pop()
        
    def push_class_symbol_stack(self):
        self.class_symbols_stack.append(self.symbol_table)
        
    def push_symbol_table_stack(self, name):
        if name not in self.symbol_table:
            self.symbol_table[name] = common.SymbolTableEntry()
        self.symbol_table[name].child = {}
        self.symbol_table = self.symbol_table[name].child
        self.symbol_table_stack.append(self.symbol_table)


    def pop_symbol_table_stack(self):
        self.symbol_table_stack.pop()
        self.symbol_table = self.symbol_table_stack[-1]

    def IsAugAssign(self):
        for item in self.current_node_stack[::-1]:
            if isinstance(item, ast.AugAssign):
                return True
            if isinstance(item, ast.Assign):
                return False
            if isinstance(item, ast.comprehension):
                return False
        return None
    
    # returns a tuple with the (variable name, is a class variable (i.e. self.x), has other attributes (i.e.x.y.x))
    def GetVariableContext(self):
        list = []
        for item in self.current_node_stack[::-1]:
            if isinstance(item, ast.Attribute):
                list.insert(0, item.attr)
                last = item
            else:
                break
        if isinstance(last.value, ast.Name):
            list.insert(0, last.value.id)
            if len(list) == 1:
                return (list[-1], False, False)
            if not self.def_class_param_stack:
                selfVal = None
            else:
                selfVal = self.def_class_param_stack[-1]
            if selfVal == list[0]:
                if len(list) == 2:
                    return (list[-1], True, False)
                else:
                    return (list[0], True, True)
            else:
                if len(list) == 1:
                    return (list[-1], False, False)
                else:
                    return (list[0], False, True)
        else:
            # ','.join(f'x' for ...)
            return (None, False, True)

    def push_def_class_param_stack(self):
        classParam = self.GetClassParameterName()
        self.def_class_param_stack.append(classParam)
        
    def pop_def_class_param_stack(self):
        self.def_class_param_stack.pop()

    def GetClassParameterName(self):
        functionDef = self.current_node_stack[-1]
        if self.IsClassFunction():
            return functionDef.args.args[0].arg
        else:
            return None

    def post_process(self):
        # any critical nodes in if conditions will be grouped by the
        # values that they are assigned to, and if anything looks fishy flag it
        # as non-concurrent, which will force a wait immediately after the call
        for critical in self.critical_nodes:
            if isinstance(critical, ast.Call):
                call_lookup_node = self.node_lookup[critical]
                if not call_lookup_node.if_stack:
                    continue
                parent = call_lookup_node.ancestors[-2]
                ok = False
                if isinstance(parent, ast.Assign) and len(parent.targets)==1 and isinstance(parent.targets[0], ast.Name):
                    symbol_name = parent.targets[0].id

                    parent_lookup_node = self.node_lookup[parent.targets[0]]
                    assigned_symbol = self.get_variable_reference(
                       symbol_name, parent_lookup_node.ancestors)
                    
                    if assigned_symbol.is_set_unambiguously_across_if_blocks():
                       ok = True
                       for writer_nodes in assigned_symbol.usage_by_types([common.SymbolTableEntry.ATTR_WRITE]):
                           if writer_nodes.if_stack and isinstance(writer_nodes.ancestors[-2], ast.Assign):
                               maybe_critical_node = writer_nodes.ancestors[-2].value
                               if not common.is_constant(maybe_critical_node) and maybe_critical_node not in self.critical_nodes:
                                   ok=False
                                   
                if not ok:
                    self.non_concurrent_critical_nodes.add(critical)
                else:
                    self.critical_nodes_if_groups[critical]=symbol_name
                    
                
            

def Scan(tree, config, parent=None):
    analyzer = VariablesAnalyzer(config, parent)
    analyzer.visit(tree)
    analyzer.post_process()
    return analyzer
