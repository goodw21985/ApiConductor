import ast

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
    def __init__(self, ancestors, if_stack):
        self.ancestors = ancestors  # the parent node stack of the current node
        self.if_stack = if_stack
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

class IfFrame:
    def __init__(self, node, if_stack):
        ast.If
        self.node =node
        self.if_stack = if_stack
        self.bodies = []
        self.conditions = []
        self.nested_statements = []
        self.blockframes = []
        loopnode = node
        while True:
            self.bodies.append(loopnode.body)
            self.blockframes.append(IfBlockFrame(len(self.blockframes),self))
            self.conditions.append(loopnode.test)
            if len(loopnode.orelse)==1 and isinstance(loopnode.orelse[0], ast.If):
                loopnode = loopnode.orelse[0]
            else:
                self.bodies.append(loopnode.orelse)
                break
    
class IfBlockFrame:
    def __init__(self, blockIndex, if_frame):
        self.is_mutating_condition=False
        self.if_frame = if_frame
        self.blockIndex= blockIndex
        
