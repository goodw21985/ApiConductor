import ast
from genericpath import samefile
from ast_transform import astor_fork


#
# a symbol table is a dictionary with the key of the symbol and the value of SymbolTableEntry
#
# the symbol table has a heirarchy reflecting a scope stack.
# a symbol table is a dictionary of symbols containng the properties below
# this is heirarchical, because some symbols create a new scope (see children)
#
# the symbol table is build using VariablesAnalyzer.
# as the AST is walked, the value of symbol table at any point is the current scope
#
# because the symbol table is heirarchical, the during parsing, the current symbol table will be
# from the relevance place in the heirarchy
#
class SymbolTableEntry:
    ATTR_READ = "read"  # name of the read attribute
    ATTR_WRITE = "write"  # name of the write attribute
    ATTR_READ_WRITE = "readwrite"  # name of the readwrite attribute
    ATTR_DECLARED = "declared"  # name of the declared attribute
    ATTR_AMBIGUOUS = "ambiguous"  # name of the declared attribute

    def __init__(self):
        self.read = []  # which nodes read this symbol
        self.write = []  # which notes write this symbol
        self.readwrite = []  # which notes read/write this symbol
        self.declared = []  # which notes declared this symbol
        self.ambiguous = (
            []
        )  # which nodes had dangerous/ambiguous access to this symbol (example, for a: a[3]=5)
        self.child = None  # this symbol is a class, function or lambda, and has a child symbol table
        self.redirect = None  # this symbol has been combined with another because of global or nonlocal
        self.notLocal = False  # true if this symbol was combined with an inner scope because of global or local

    def __getitem__(self, key):
        if key == SymbolTableEntry.ATTR_READ:
            return self.read
        elif key == SymbolTableEntry.ATTR_WRITE:
            return self.write
        elif key == SymbolTableEntry.ATTR_READ_WRITE:
            return self.readwrite
        elif key == SymbolTableEntry.ATTR_DECLARED:
            return self.declared
        elif key == SymbolTableEntry.ATTR_AMBIGUOUS:
            return self.ambiguous
        else:
            raise ValueError(
                "SymbolTableEntry does not have an attribute named '" + key + "'"
            )


#
# NodeCrossReference is a sidecar structure where additional intellengence about a node is stored without
# modifying the underlying node.
#
# self.current_node_lookup contains this value for a node when the visit* is called.
#
# self.node_lookup[node] will return the following class instance as additional information that has been
# accumulated so far about this node.   TODO:  is ast.node a valid key for a dictionary?
#
class NodeCrossReference:
    def __init__(self, ancestors):
        self.ancestors = ancestors  # the parent node stack of the current node
        self.symbol = None  # the Symbol table entry for this if node, if this node references a symbol
        self.dependency = []  # list of critical nodes that depend on this node
        self.assigned_concurrency_group = None  # code grouping
        self.reassigned = (
            None  # name of expression if assigned to newly created variable
        )
        self.dependency_visited = (
            False  # used to identify nodes not followed in dependency analysis
        )

class Config:
    def __init__(self):
        self.use_async = False
        self.wrap_in_function_def = False
        self.awaitable_functions = []
        self.module_blacklist = None
        self.log = False


# This is the base class for the llmPython AST walker, and it keeps track of symbol tables and cross references implicitly
#
class ScopeAnalyzer(ast.NodeTransformer):
    def __init__(self, copy=None):
        self.symbol_table_stack = None  # no symbol table stack exists before VariablesAnalyzer is being or has been run
        self.symbol_table = None
        self.node_stack = []
        self.current_node_stack = []
        self.is_lambda_count = 0
        self.class_symbols_stack = []
        self.def_class_param_stack = []
        self.node_lookup = {}
        self.critical_nodes = None
        self.critical_node_names = None
        self.have_symbol_table = False
        self.global_return_statement = None
        self.tracking = None
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
        if isinstance(copy, Config):
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
            self.current_node_stack = []
            self.is_lambda_count = 0
            self.class_symbols_stack = []
            self.def_class_param_stack = []
            self.critical_nodes = copy.critical_nodes
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
        if self.have_symbol_table:
            if node not in self.node_lookup:
                self.current_node_lookup = NodeCrossReference(self.current_node_stack)
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
        if self.have_symbol_table:
            if node not in self.node_lookup:
                self.current_node_lookup = NodeCrossReference(self.current_node_stack)
                self.node_lookup[node] = self.current_node_lookup
            else:
                self.current_node_lookup = self.node_lookup[node]
            if self.pass_name == "dependency":
                self.current_node_lookup.dependency_visited = True
        if self.tracking:
            if self.tracking in self.current_node_lookup.dependency:
                # stop when we hit the same node
                self.node_stack.pop()
                return node
            elif node != self.tracking:
                self.current_node_lookup.dependency.append(self.tracking)

            if node != self.tracking and node in self.critical_nodes:
                # stop when we see another critical node
                self.node_stack.pop()
                return node

        ret = super().visit(node)
        self.node_stack.pop()
        return ret

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
                self.Log(node, "set node_lookup lambda")
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

    def ConcurrencySafeContext(self, nodestack):
        for node in nodestack:
            if isinstance(node, ast.For):
                return False
            if isinstance(node, ast.While):
                return False
            if isinstance(node, ast.With):
                return False
            if isinstance(node, ast.Try):
                return False
        return True

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
