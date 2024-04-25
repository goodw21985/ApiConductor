import ast
from . import Util
from . import scope_analyzer

class VariablesAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        super().__init__(copy) 
        self.symbol_table_stack = []
        self.symbol_table_stack.append({})
        self.symbol_table = self.symbol_table_stack[-1];

    def visit_Name2(self, node):
        name = node.id
        group = self.node_read
        if not self.IgnoreSymbol(node):
            if isinstance(node.ctx, ast.Store):
                q=self.IsAugAssign()
                if q==True:
                    group = self.node_read_write
                elif q==False:
                    group = self.node_write
                else:
                    group = self.node_ambiguous

            self.add_variable_reference(name, group, self.current_node_stack)

    def visit_Lambda2(self, node):        
        for arg in node.args.args:
            self.add_variable_reference(arg.arg,self.node_read,self.current_node_stack)
            
    def visit_Attribute(self, node):
        (name, isClass, isComplex)=self.GetVariableContext()
        if isinstance(node.ctx, ast.Load):
            group = self.node_read
        elif isinstance(node.ctx, ast.Store):
            q=self.IsAugAssign()
            if q==True:
                group = self.node_read_write
            elif q==False:
                group = self.node_write
            else:
                group = self.node_ambiguous

        if isComplex:
            if group!=self.node_read:
                group = self.node_ambiguous

        if isClass:            
            self.add_class_variable_reference(name, group, self.current_node_stack)
        else:
            self.add_variable_reference(name, group, self.current_node_stack)
        self.generic_visit(node)

    def visit_arg2(self,node):
        if self.def_class_param_stack[-1]!=node.arg:
            self.add_variable_reference(node.arg,self.node_declared,self.current_node_stack)
        
    def visit_Global(self, node):
        for target in node.names:
            root=self.symbol_table_stack[0]
            self.Redirect(target, root)
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        for target in node.names:
            for ancestor in self.symbol_table_stack[:-1][::-1]:
                if not self.Redirect(target, ancestor):
                    break
        self.generic_visit(node)

    def Redirect(self, key, value):
        if key not in self.symbol_table:
            self.symbol_table[key] = {}
        
        self.symbol_table[key][self.node_redirect]=value
        if key not in value:
            value[key]={}
        return self.node_redirect in value
        
    def add_variable_reference(self, key, group, value):
        dictionary = self.find_frame(key)
        if key not in dictionary:
            dictionary[key] = {}
        item = dictionary[key]
        if (self.node_redirect in item):
            sub = item[self.node_redirect]
            if key not in sub:
                sub[key]={}
            item=sub[key]
       
        if group not in item:
            item[group]=[]
        list = item[group]
        list.append(value)

    def add_class_variable_reference(self, key, group, value):
        dictionary = self.class_symbols_stack[-1]
        if key not in dictionary:
            dictionary[key] = {}
        item = dictionary[key]
        if group not in dictionary:
            item[group]=[]
        list = item[group]
        list.append(value)

    def push_symbol_table_stack(self, name):
        if name not in self.symbol_table:
            self.symbol_table[name] = {}
        self.symbol_table[name][self.node_children] = {} 
        self.symbol_table=self.symbol_table[name][self.node_children]
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
      
def Scan(tree, parent=None):
    analyzer = VariablesAnalyzer(parent)
    analyzer.visit(tree)
    return analyzer

