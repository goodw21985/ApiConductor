import ast
from multiprocessing import Value
from . import Util

class ScopeAnalyzer(ast.NodeTransformer):
    #
    # the symbol table has a heirarchy reflecting a scope stack. 
    # a symbol table is a dictionary of symbols containng the properties below
    # this is heirarchical, because some symbols create a new scope (see children)
    #
    # the symbol table is build using VariablesAnalyzer.
    # as the AST is walked, the value of symbol table at any point is the current scope
    #
    # lookup_symbol(key) can be used to find the symbol entry that respects scope 
    # TODO: lookup_symbol should accept a node....  because untangling symbols in nodes is weird
    #
    # properties for each symbol in the symbol table
    node_read = "r"             # this node is read in these locations
    node_write = "w"            # this node is modified in these locations
    node_read_write = "rw"      # this node is read and modified (i.e. +=) in these locations
    node_declared = ":"         # this node is declared in a function or lambda at these locations (should be 1)
    node_ambiguous = "m"        # this node has some ambiguous modification that cannot be untangled  (e.g. 1a.b[3]=2)
    node_children = "children"  # this node is a class, function or lambda, and has a child scope
    node_redirect = "redirect"  # this node has been redirected to another scope because of gloabal or nonlocal
    
    #
    # there is a node cross reference
    # nodelookup[node]
    #  
    # this contains the parent node, and also the symbol (is it is a name, or attribute, etc.)
    # nodelookup[node].parents
    # nodelookup[node].symbol 
    node_parents = "parents"
    node_symbol="symbol"
    
    def __init__(self, copy = None):
        if copy == None:
            self.symbol_table_stack = None  # no symbol table exists until VariablesAnalyzer is run
            self.symbol_table = None
            self.node_stack = [] 
            self.current_node_stack = []
            self.isLambdaCount=0       
            self.class_symbols_stack = []
            self.def_class_param_stack = []
            self.nodelookup = {}
            self.awaitable_function_list = None
        else:
            self.symbol_table = copy.symbol_table
            self.symbol_table_stack = []
            self.symbol_table_stack.append(self.symbol_table)
            self.node_stack = []
            self.current_node_stack = []
            self.isLambdaCount=0       
            self.class_symbols_stack = []
            self.def_class_param_stack = []
            self.awaitable_function_list = copy.awaitable_function_list
            self.nodelookup = {}
        
    def visit(self, node):
        self.node_stack.append(node)
        self.current_node_stack = self.node_stack[:]
        self.current_node_lookup = {self.node_parents: self.current_node_stack}
        self.nodelookup[node] = self.current_node_lookup
        super().visit(node)
        self.node_stack.pop()
        
    def visit_FunctionDef(self, node):
        classParam=self.GetClassParameterName()
        self.def_class_param_stack.append(classParam)
        
        # Enter a new scope (function)
        
        self.push_symbol_table_stack(node.name)
        self.visit_FunctionDef2(node)
        self.generic_visit(node)
        
        # Exit the scope (function)
        
        self.pop_symbol_table_stack()
        self.def_class_param_stack.pop()

    def visit_FunctionDef2(self, node):
        pass

    def visit_Name(self, node):
        self.visit_Name2(node)
        
        if not self.IgnoreSymbol(node):
            self.current_node_lookup[self.node_symbol]=  self.get_variable_reference(node.id,  self.current_node_stack);
        self.generic_visit(node)

    def visit_Name2(self, node):
        pass

    def visit_arg(self,node):
        self.visit_arg2(node)
        if self.def_class_param_stack[-1]!=node.arg:
            self.current_node_lookup[self.node_symbol]=  self.get_variable_reference(node.arg,  self.current_node_stack);        
        self.generic_visit(node)

    def visit_arg2(self, node):
        pass

    def visit_Attribute(self, node):        
        self.visit_Attribute2(self, node)
        (name ,isClass, _) = self.GetVariableContext()
        if isClass:     
            self.current_node_lookup[self.node_symbols] = self.get_class_variable_reference(name, self.current_node_stack)
        else:
            self.current_node_lookup[self.node_symbols] = self.get_variable_reference(name, self.current_node_stack)
        self.generic_visit(node)

    def visit_Attribute2(self, node):
        pass

    def visit_ClassDef(self, node):
        self.push_symbol_table_stack(node.name)
        self.class_symbols_stack.append(self.symbol_table)
        self.generic_visit(node)
        self.pop_symbol_table_stack()
        self.class_symbols_stack.pop()

    def visit_Lambda(self, node):        
        self.push_symbol_table_stack('lambda')
        self.visit_Lambda2(node)
        for arg in node.args.args:
            self.nodelookup[node][self.node_symbol]=self.get_variable_reference(arg.arg,self.current_node_stack)
        self.isLambdaCount+=1
        self.generic_visit(node)
        self.isLambdaCount-=1
        self.pop_symbol_table_stack()
        
    def visit_Lambda2(self, node):        
         pass
 
    def visit_AugAssign(self, node):
        self.generic_visit(node)
        
    def push_symbol_table_stack(self, name):        
        if self.symbol_table_stack is not None:
            self.symbol_table=self.symbol_table[name][self.node_children]
            self.symbol_table_stack.append(self.symbol_table)
        
    def pop_symbol_table_stack(self):      
        if self.symbol_table_stack is not None:
            self.symbol_table_stack.pop()
            self.symbol_table = self.symbol_table_stack[-1]
        
    def find_symbol(self, key):
        sym = self.find_frame(key)[key]
        while (self.Redirect in sym):
            sym = sym[self.Redirect][key]
        return sym
  
    def find_frame(self, key):
        latest_object_with_key = None
        for obj in reversed(self.symbol_table_stack):
            if key in obj:
                latest_object_with_key = obj
                break

            # only lambdas can implicitly get scope broadened
            if self.isLambdaCount == 0: break
        if latest_object_with_key is not None:
            return latest_object_with_key
        else:
            return self.symbol_table_stack[-1] if self.symbol_table_stack else None

    def IgnoreSymbol(self, node):
        if self.def_class_param_stack and self.def_class_param_stack[-1]==node.id:
            return True
        if isinstance(node.ctx, ast.Load):
            parent = self.current_node_stack[-2]
            group = self.node_read
            if parent and isinstance(parent, ast.FunctionDef):
                return True
        return False
    
    def Redirect(self, key, value):
        pass
        
    def GetRootTargetID(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self.GetRootTargetId(node.value)
        else:
            raise ValueError

    def IsClassFunction(self):
        cur=self.current_node_stack[-1]
        if self.IsStaticMethod(cur):
            return False
        for item in self.current_node_stack[:-1][::-1]:
            if isinstance(item, ast.FunctionDef):
                return False
            elif isinstance(item, ast.ClassDef):
                return True
        return False

    def IsStaticMethod(self, node):
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
               if d.id=="staticmethod": return True
        return False

    def GetClassParameterName(self):
        functionDef=self.current_node_stack[-1]
        if self.IsClassFunction():
            return functionDef.args.args[0].arg
        else:
            return None
        
    def get_variable_reference(self, key, value):
        dictionary = self.find_frame(key)
        item = dictionary[key]
        if (self.node_redirect in item):
            sub = item[self.node_redirect]
            if key not in sub:
                sub[key]={}
            item=sub[key]
        return item
       
    def get_class_variable_reference(self, key, value):
        dictionary = self.find_frame(key)
        item = dictionary[key]
        return item
       
    def GetVariableContext(self):
        list=[]        
        for item in self.current_node_stack[::-1]:
            if isinstance(item, ast.Attribute):
                list.insert(0, item.attr)
                last=item
            else:
                break
        list.insert(0,last.value.id)
        if len(list) == 1:
            return (list[-1],False, False)
        if  not self.def_class_param_stack:
            selfVal= None
        else:
            selfVal = self.def_class_param_stack[-1]
        if selfVal==list[0]:
            if (len(list)==2):
                return (list[-1], True, False)
            else:
                return (list[0], True, True)
        else:
            if (len(list)==1):
                return (list[-1], False, False)
            else:
                return (list[0], False, True)
                    
def Scan(tree, parent=None):
    analyzer = ScopeAnalyzer(parent)
    analyzer.visit(tree)
    return analyzer

