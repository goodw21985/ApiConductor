import ast
from ast_transform import astor_fork
from ast_transform import common


# This is the base class for the llmPython AST walker, and it keeps track of symbol tables and cross references implicitly
#
# Each pass over the code that is executed inherits from this class
class ScopeAnalyzer(ast.NodeTransformer):
    # any state that should persist between passes is copied during class construction using the copy construct in the __init__ function 
    def __init__(self, copy=None):
        self.symbol_table = None
        self.node_stack = []
        self.if_stack = []
        self.if_lookup = {}
        self.current_node_stack = []
        self.current_if_stack = []
        self.scope_broadened = 0
        self.node_lookup = {}
        self.critical_nodes = None
        self.critical_node_names = None
        self.non_concurrent_critical_nodes = None
        self.critical_nodes_if_groups = None        
        self.global_return_statement = None
        self.tracking = None
        self.in_condition_expr=False
        self.mutating_condition_expr=False
        self.critical_dependencies = None
        self.concurrency_group_code = None
        self.concurrency_groups = None
        self.aggregated=None
        self.null_symbol_table_entry = common.SymbolTableEntry()
        self.module_blacklist = [
            "threading",
            "io",
            "os",
            "sys",
            "subprocess",
            "coroutines",
            "socket",
            "shutil",
            "fcntl",
            "events",
            "runners",
            "mmap",
            "tempfile",
            "pickle",
            "eval",
            "exec",
            "ctypes",
            "cffi",
            "signal",
            "_contextvars",
            "contextvars",
        ]
        if isinstance(copy, common.Config):
            self.module_blacklist = copy.module_blacklist or self.module_blacklist
            self.config = copy
        elif copy == None:
            pass
        else:
            self.config = copy.config
            self.global_return_statement = copy.global_return_statement
            self.symbol_table = copy.symbol_table
            self.node_stack = []
            self.if_stack = []
            self.if_lookup = copy.if_lookup
            self.current_node_stack = []
            self.current_if_stack = []
            self.scope_broadened = 0
            self.critical_nodes = copy.critical_nodes
            self.aggregated=copy.aggregated
            self.non_concurrent_critical_nodes = copy.non_concurrent_critical_nodes
            self.critical_nodes_if_groups = copy.critical_nodes_if_groups            
            self.critical_node_names = copy.critical_node_names
            self.node_lookup = copy.node_lookup
            self.tracking = None
            self.critical_dependencies = copy.critical_dependencies
            self.concurrency_group_code = None
            self.concurrency_groups = copy.concurrency_groups
            self.module_blacklist = copy.module_blacklist
        self.Log("*** " + self.pass_name)

    def new_critical_node_name(self):
        return "C" + str(len(self.critical_node_names))

    def skip_visit(self, node):
        self.node_stack.append(node)
        self.current_node_stack = self.node_stack[:]
        self.visit_pre(node)
        if isinstance(node, ast.Name):
            self.skip_visit_Name(node)
        else:
            raise ValueError
        self.node_stack.pop()

    def visit(self, node):
        self.node_stack.append(node)
        self.current_node_stack = self.node_stack[:]
        self.visit_pre(node)

        # returns True if following should stop here
        if self.track_dependency(node):
            ret = node
        else:
            ret = super().visit(node)
        self.node_stack.pop()
        return ret

    def visit_pre(self, node):
        self.current_node_lookup = self.node_lookup[node]
        
    def track_dependency(self, node):
        return False

    def visit_Global(self, node):
        raise ValueError("global statement is not safe")
        self.generic_visit(node)
        return node

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id in (
                    "os",
                    "sys",
                    "socket",
                    "builtins",
                    "io",
                    "asyncio",
                ):
                    raise ValueError("monkey patching detected")

        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self.push_def_class_param_stack()

        # Enter a new scope (function)

        self.push_symbol_table_stack(node)
        ret = self.visit_FunctionDef2(node)
        self.generic_visit(node)

        # Exit the scope (function)

        self.pop_symbol_table_stack()
        self.pop_def_class_param_stack()
        return ret

    def push_def_class_param_stack(self):
        pass
            
    def pop_def_class_param_stack(self):
        pass

    def visit_FunctionDef2(self, node):
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        return node

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in self.module_blacklist:
                raise ValueError("blacklisted module")
        self.generic_visit(node)
        return node

    def visit_ImportFrom(self, node):
        if node.module in self.module_blacklist:
            raise ValueError("blacklisted module")
        self.generic_visit(node)

    def skip_visit_Name(self, node):
        pass

    def visit_If(self, node):
        if node in self.if_lookup:
            current_if_frame = self.if_lookup[node]
        else:
            current_if_frame = common.IfFrame(node, self.current_if_stack)

        for i in range(len(current_if_frame.bodies)):
            self.if_stack.append(current_if_frame.blockframes[i])
            self.current_if_stack = self.if_stack[:]
            if i<len(current_if_frame.conditions):
                self.in_condition_expr = True
                self.mutating_condition_expr=False
                self.visit(current_if_frame.conditions[i])
                if self.mutating_condition_expr:
                    current_if_frame.blockframes[i].is_mutating_condition=True
                self.in_condition_expr = False
                
            for statement in current_if_frame.bodies[i]:
                self.visit(statement)
            
            self.if_stack.pop()
            self.current_if_stack = self.if_stack[:]

        return node
        
    def visit_Name(self, node):
        ret = self.visit_Name2(node)
        self.generic_visit(node)
        return ret

    def visit_Name2(self, node):
        return node

    def visit_Call(self, node):
        ret = self.visit_Call2(node)
        self.generic_visit(node)
        return ret

    def visit_Call2(self, node):
        return node

    def visit_arg(self, node):
        ret = self.visit_arg2(node)
        self.generic_visit(node)
        return ret

    def visit_arg2(self, node):
        return node

    def visit_Attribute(self, node):
        ret = self.visit_Attribute2(node)
        self.generic_visit(node)
        return ret

    def visit_Attribute2(self, node):
        return node

    def visit_ClassDef(self, node):
        self.push_symbol_table_stack(node)
        self.push_class_symbol_stack()

        self.generic_visit(node)
        self.pop_symbol_table_stack()
        self.pop_class_symbol_stack()
        return node

    def pop_class_symbol_stack(self):
        pass
        
    def push_class_symbol_stack(self):
        pass
         
    def visit_GeneratorExp(self, node):
        self.push_symbol_table_stack(node)
        self.scope_broadened += 1
        ret = self.visit_GeneratorExp2(node)

        # need to visit the generators first, so it does not seem non-immutable
        self.scope_broadened -= 1
        self.pop_symbol_table_stack()
        return ret

    def visit_GeneratorExp2(self, node):
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        return node
        
    def visit_DictComp(self, node):
        self.push_symbol_table_stack(node)
        self.scope_broadened += 1
        ret = self.visit_DictComp2(node)

        self.scope_broadened -= 1
        self.pop_symbol_table_stack()
        return ret

    def visit_DictComp2(self, node):
        # need to visit the generators first, so it does not seem non-immutable
        for g in node.generators:
            self.visit(g)
        self.visit(node.key)
        self.visit(node.value)
        return node
        
    def visit_SetComp(self, node):
        self.push_symbol_table_stack(node)
        self.scope_broadened += 1

        ret = self.visit_SetComp2(node)

        # need to visit the generators first, so it does not seem non-immutable
        self.scope_broadened -= 1
        self.pop_symbol_table_stack()
        return ret

    def visit_SetComp2(self, node):
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        return node
        
    def visit_ListComp(self, node):
        self.push_symbol_table_stack(node)
        self.scope_broadened += 1
        ret = self.visit_ListComp2(node)

        self.scope_broadened -= 1
        self.pop_symbol_table_stack()
        return ret

    def visit_ListComp2(self, node):
        # need to visit the generators first, so it does not seem non-immutable
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        return node
        

    def visit_Lambda(self, node):
        self.push_symbol_table_stack(node)
        ret = self.visit_Lambda2(node)

        self.scope_broadened += 1
        self.generic_visit(node)
        self.scope_broadened -= 1
        self.pop_symbol_table_stack()
        return ret

    def visit_Lambda2(self, node):
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        return node

    def push_symbol_table_stack(self, node):
        pass
    
    def pop_symbol_table_stack(self):
        pass


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
        cur = self.current_node_stack[-1]
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
                if d.id == "staticmethod":
                    return True
        return False

    def get_variable_reference(self, key, value):
        if key==None:
            return self.null_symbol_table_entry
        dictionary = self.find_frame(key)
        item = dictionary[key]
        if item.redirect:
            sub = item[self.node_redirect]
            if key not in sub:
                sub[key] = {}
            item = sub[key]
        return item

    #def get_class_variable_reference(self, key, value):
    #    if self.have_symbol_table:
    #        return None
    #    dictionary = self.find_frame(key)
    #    item = dictionary[key]
    #    return item

    def Log(self, node, msg=None):
        if not self.config.log:
            return
        if msg == None:
            print(node)
        elif isinstance(node, ast.Load):
            pass
        elif isinstance(node, ast.Add):
            pass
        elif isinstance(node, ast.Del):
            pass
        elif isinstance(node, ast.Store):
            pass
        elif isinstance(node, ast.keyword):
            pass
        elif isinstance(node, ast.unaryop):
            pass
        elif isinstance(node, ast.operator):
            pass
        elif isinstance(node, ast.cmpop):
            pass
        else:
            self.Logprint(node, msg)

    def Logprint(self, node, msg):
        # try:
        s = astor_fork.to_source(node).strip()
        if len(s) > 40:
            s = s[0:40] + "..."
        # except Exception as e:
        #    s = str(e)

        parent = ""
        if len(self.current_node_stack) > 1:
            parent = str(self.current_node_stack[-2])
        line = str(node) + " " + str(parent) + " '" + s + "' " + msg
        print(line)


def Scan(tree, parent=None):
    analyzer = ScopeAnalyzer(parent)
    analyzer.visit(tree)
    return analyzer
