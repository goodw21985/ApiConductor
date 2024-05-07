import ast
from ast_transform import astor_fork
from ast_transform import common


# This is the base class for the llmPython AST walker, and it keeps track of symbol tables and cross references implicitly
#
class ScopeAnalyzer(ast.NodeTransformer):
    def __init__(self, copy=None):
        self.symbol_table_stack = None  # no symbol table stack exists before VariablesAnalyzer is being or has been run
        self.symbol_table = None
        self.node_stack = []
        self.if_stack = []
        self.if_lookup = {}
        self.current_node_stack = []
        self.current_if_stack = []
        self.is_lambda_count = 0
        self.class_symbols_stack = []
        self.def_class_param_stack = []
        self.node_lookup = {}
        self.critical_nodes = None
        self.critical_node_names = None
        self.non_concurrent_critical_nodes = None
        self.critical_nodes_if_groups = None        
        self.have_symbol_table = False
        self.global_return_statement = None
        self.tracking = None
        self.in_condition_expr=False
        self.mutating_condition_expr=False
        self.critical_dependencies = None
        self.concurrency_group_code = None
        self.concurrency_groups = None
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
            self.have_symbol_table = copy.have_symbol_table
            self.global_return_statement = copy.global_return_statement
            self.symbol_table = copy.symbol_table
            self.have_symbol_table = copy.symbol_table is not None
            self.symbol_table_stack = [self.symbol_table]
            self.node_stack = []
            self.if_stack = []
            self.if_lookup = copy.if_lookup
            self.current_node_stack = []
            self.current_if_stack = []
            self.is_lambda_count = 0
            self.class_symbols_stack = []
            self.def_class_param_stack = []
            self.critical_nodes = copy.critical_nodes
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
        if node not in self.node_lookup:
            self.current_node_lookup = common.NodeCrossReference(self.current_node_stack,self.current_if_stack)
            self.node_lookup[node] = self.current_node_lookup
        else:
            self.current_node_lookup = self.node_lookup[node]
        if isinstance(node, ast.Name):
            self.skip_visit_Name(node)
        else:
            raise ValueError
        self.node_stack.pop()

    def visit(self, node):
        self.node_stack.append(node)
        self.current_node_stack = self.node_stack[:]
        if node not in self.node_lookup:
            self.current_node_lookup = common.NodeCrossReference(self.current_node_stack, self.current_if_stack)
            self.node_lookup[node] = self.current_node_lookup
        else:
            self.current_node_lookup = self.node_lookup[node]
        # returns True if following should stop here
        if self.track_dependency(node):
            ret = node
        else:
            ret = super().visit(node)
        self.node_stack.pop()
        return ret

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
        classParam = self.GetClassParameterName()
        self.def_class_param_stack.append(classParam)

        # Enter a new scope (function)

        self.push_symbol_table_stack(node.name)
        ret = self.visit_FunctionDef2(node)
        self.generic_visit(node)

        # Exit the scope (function)

        self.pop_symbol_table_stack()
        self.def_class_param_stack.pop()
        return ret

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
        self.current_node_lookup.symbol = self.get_variable_reference(
            node.id, self.current_node_stack
        )

    def visit_If(self, node):
        if node in self.if_lookup:
            current_if_frame = self.if_lookup[node]
        else:
            current_if_frame = common.IfFrame(node, self.current_if_stack)

        for i in range(len(current_if_frame.bodies)):
            self.if_stack.append(current_if_frame.blockframes[i])
            self.current_if_stack = self.if_stack[:]
            if i<len(current_if_frame.bodies)-1:
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
        if self.have_symbol_table:
            if not self.IgnoreSymbol(node):
                self.current_node_lookup.symbol = self.get_variable_reference(
                    node.id, self.current_node_stack
                )

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
        if self.have_symbol_table:
            if (
                not self.def_class_param_stack
                or self.def_class_param_stack[-1] != node.arg
            ):
                self.current_node_lookup.symbol = self.get_variable_reference(
                    node.arg, self.current_node_stack
                )
        ret = self.visit_arg2(node)
        self.generic_visit(node)
        return ret

    def visit_arg2(self, node):
        return node

    def visit_Attribute(self, node):
        if self.have_symbol_table:
            (name, isClass, _) = self.GetVariableContext()
            if isClass:
                self.current_node_lookup.symbol = self.get_class_variable_reference(
                    name, self.current_node_stack
                )
            else:
                self.current_node_lookup.symbol = self.get_variable_reference(
                    name, self.current_node_stack
                )
        ret = self.visit_Attribute2(node)
        self.generic_visit(node)
        return ret

    def visit_Attribute2(self, node):
        return node

    def visit_ClassDef(self, node):
        self.push_symbol_table_stack(node.name)
        self.class_symbols_stack.append(self.symbol_table)
        self.generic_visit(node)
        self.pop_symbol_table_stack()
        self.class_symbols_stack.pop()
        return node

    def visit_Lambda(self, node):
        self.push_symbol_table_stack("lambda")
        if self.have_symbol_table:
            for arg in node.args.args:
                self.node_lookup[node].symbol = self.get_variable_reference(
                    arg.arg, self.current_node_stack
                )
        ret = self.visit_Lambda2(node)

        self.is_lambda_count += 1
        self.generic_visit(node)
        self.is_lambda_count -= 1
        self.pop_symbol_table_stack()
        return ret

    def visit_Lambda2(self, node):
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        return node

    def push_symbol_table_stack(self, name):
        if self.symbol_table_stack is not None:
            self.symbol_table = self.symbol_table[name].child
            self.symbol_table_stack.append(self.symbol_table)

    def pop_symbol_table_stack(self):
        if self.symbol_table_stack is not None:
            self.symbol_table_stack.pop()
            self.symbol_table = self.symbol_table_stack[-1]

    def find_symbol(self, key):
        sym = self.find_frame(key)[key]
        while self.Redirect in sym:
            sym = sym[self.Redirect][key]
        return sym

    def find_frame(self, key):
        latest_object_with_key = None
        for obj in reversed(self.symbol_table_stack):
            if key in obj:
                latest_object_with_key = obj
                break

            # only lambdas can implicitly get scope broadened
            if self.is_lambda_count == 0:
                break
        if latest_object_with_key is not None:
            return latest_object_with_key
        else:
            return self.symbol_table_stack[-1] if self.symbol_table_stack else None

    def IgnoreSymbol(self, node):
        if self.def_class_param_stack and self.def_class_param_stack[-1] == node.id:
            return True
        if isinstance(node.ctx, ast.Load):
            parent = self.current_node_stack[-2]
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

    def GetClassParameterName(self):
        functionDef = self.current_node_stack[-1]
        if self.IsClassFunction():
            return functionDef.args.args[0].arg
        else:
            return None

    def get_variable_reference(self, key, value):
        dictionary = self.find_frame(key)
        item = dictionary[key]
        if item.redirect:
            sub = item[self.node_redirect]
            if key not in sub:
                sub[key] = {}
            item = sub[key]
        return item

    def get_class_variable_reference(self, key, value):
        if self.have_symbol_table:
            return None
        dictionary = self.find_frame(key)
        item = dictionary[key]
        return item

    def GetVariableContext(self):
        list = []
        for item in self.current_node_stack[::-1]:
            if isinstance(item, ast.Attribute):
                list.insert(0, item.attr)
                last = item
            else:
                break
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
