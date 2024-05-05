import ast
from . import scope_analyzer
from . import common


class VariablesAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, config, copy):
        self.pass_name = "variables"
        self.config = config
        super().__init__(copy)
        self.symbol_table_stack = []
        self.symbol_table_stack.append({})
        self.symbol_table = self.symbol_table_stack[-1]
        self.critical_nodes = []
        self.critical_node_names = {}
        self.global_return_statement = None
    
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

            self.add_variable_reference(name, group, self.current_node_stack)
        return node

    # looking for implicit async function usage.
    def visit_Call2(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.config.awaitable_functions:
                if self.ConcurrencySafeContext(self.node_stack):
                    self.critical_nodes.append(node)
                    self.critical_node_names[node]=self.new_critical_node_name()
        return node

    def visit_Lambda2(self, node):
        for arg in node.args.args:
            self.add_variable_reference(
                arg.arg,
                common.SymbolTableEntry.ATTR_READ,
                self.current_node_stack,
            )
        return node

    def visit_Attribute2(self, node):
        (name, isClass, isComplex) = self.GetVariableContext()
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
            self.add_class_variable_reference(name, group, self.current_node_stack)
        else:
            self.add_variable_reference(name, group, self.current_node_stack)
        return node

    def visit_arg2(self, node):
        if not self.def_class_param_stack or self.def_class_param_stack[-1] != node.arg:
            self.add_variable_reference(
                node.arg,
                common.SymbolTableEntry.ATTR_DECLARED,
                self.current_node_stack,
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

        item.usage.append((group,value))

    def add_class_variable_reference(self, key, group, value):
        dictionary = self.class_symbols_stack[-1]
        if key not in dictionary:
            dictionary[key] = common.SymbolTableEntry()
        dictionary[key].usage.append((group,value))

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
        return None
    
    def post_process(self, syms):
        for name in syms.keys():
            v = syms[name]
            if v.child:
                self.post_process(v.child)
            if v.redirect:
                pass
            pass # I think the cross reference is badly organized
            
        pass

def Scan(tree, config, parent=None):
    analyzer = VariablesAnalyzer(config, parent)
    analyzer.visit(tree)
    analyzer.post_process(analyzer.symbol_table)
    return analyzer
