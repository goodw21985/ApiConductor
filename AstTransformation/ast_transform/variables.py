import ast
from . import Util

class ScopeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.symbol_table_stack = []
        self.symbol_table_stack.append({})
        self.symbol_table = self.symbol_table_stack[-1];
        self.node_stack = []
        self.current_node_stack = []
        self.isLambdaCount=0       
        self.class_symbols_stack = []
        self.def_class_param_stack = []
        
    def visit(self, node):
        self.node_stack.append(node)
        self.current_node_stack = self.node_stack[:]
        super().visit(node)
        self.node_stack.pop()
        
    def visit_FunctionDef(self, node):
        classParam=self.GetClassParameterName()
        self.def_class_param_stack.append(classParam)
        # Enter a new scope (function)
        self.push_symbol_table_stack(node.name)
        self.generic_visit(node)
        # Exit the scope (function)
        self.pop_symbol_table_stack()
        self.def_class_param_stack.pop()
        

    def visit_ClassDef(self, node):
        self.push_symbol_table_stack(node.name)
        self.class_symbols_stack.append(self.symbol_table)
        self.generic_visit(node)
        self.pop_symbol_table_stack()
        self.class_symbols_stack.pop()

    def visit_arg(self,node):
        if self.def_class_param_stack[-1]==node.arg:
            return
        self.add_variable_reference(node.arg,":",self.current_node_stack)
        self.generic_visit(node)
        
    def visit_Lambda(self, node):        
        self.push_symbol_table_stack('lambda')
        for arg in node.args.args:
            self.add_variable_reference(arg.arg,"r",self.current_node_stack)
        self.isLambdaCount+=1
        self.generic_visit(node)
        self.isLambdaCount-=1
        self.pop_symbol_table_stack()
        
    def visit_AugAssign(self, node):
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        (name, isClass, isComplex)=self.GetVariableContext()
        if isinstance(node.ctx, ast.Load):
            group = "r"
        elif isinstance(node.ctx, ast.Store):
            q=self.IsAugAssign()
            if q==True:
                group = "rw"
            elif q==False:
                group = "w"
            else:
                group = "m"

        if isComplex:
            if group!="r":
                group = "m"

        if isClass:            
            self.add_class_variable_reference(name, group, self.current_node_stack)
        else:
            self.add_variable_reference(name, group, self.current_node_stack)
        self.generic_visit(node)

    def visit_Name(self, node):
        name = node.id
        if self.def_class_param_stack and self.def_class_param_stack[-1]==name:
            return

        if isinstance(node.ctx, ast.Load):
            parent = self.current_node_stack[-2]
            group = "r"
            if parent and isinstance(parent, ast.FunctionDef):
                return
        elif isinstance(node.ctx, ast.Store):
            q=self.IsAugAssign()
            if q==True:
                group = "rw"
            elif q==False:
                group = "w"
            else:
                group = "m"

        self.add_variable_reference(name, group, self.current_node_stack)
        self.generic_visit(node)

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

    def push_symbol_table_stack(self, name):
        if name not in self.symbol_table:
            self.symbol_table[name] = {}
        self.symbol_table[name]["children"] = {} 
        self.symbol_table=self.symbol_table[name]["children"]
        self.symbol_table_stack.append(self.symbol_table)
        
    def pop_symbol_table_stack(self):      
        self.symbol_table_stack.pop()
        self.symbol_table = self.symbol_table_stack[-1]
        
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

    def Redirect(self, key, value):
        if key not in self.symbol_table:
            self.symbol_table[key] = {}
        
        self.symbol_table[key]["redirect"]=value
        if key not in value:
            value[key]={}
        return "redirect" in value
        
    def add_variable_reference(self, key, group, value):
        dictionary = self.find_frame(key)
        if key not in dictionary:
            dictionary[key] = {}
        item = dictionary[key]
        if ("redirect" in item):
            sub = item["redirect"]
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
        
    def IsAugAssign(self):
        for item in self.current_node_stack[::-1]:
            if isinstance(item, ast.AugAssign):
                return True
            if isinstance(item, ast.Assign):
                return False
        return None
    

def Scan(tree):
    analyzer = ScopeAnalyzer()
    analyzer.visit(tree)
    return analyzer.symbol_table
