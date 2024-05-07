import ast
import sys

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

    BEHAVIOR_IMMUTABLE = "immutable"
    BEHAVIOR_SHARED_CRITICAL = "shared_critical"
    BEHAVIOR_UNUSED = "unused"

    def __init__(self):
        self.usage = []
        self.behavior = set([])
        self.child = None  # this symbol is a class, function or lambda, and has a child symbol table
        self.redirect = None  # this symbol has been combined with another because of global or nonlocal
        self.notLocal = False  # true if this symbol was combined with an inner scope because of global or local

    def add_usage(self, attr, node_cross_reference):
        self.usage.append((attr, node_cross_reference))
        
    def usage_by_types(self, match_values):
        return [item[1] for item in self.usage if item[0] in match_values]
        
    def GetTerminalNode(self):
        if not self.child and len(self.usage)==1:
            tuple1=self.usage[0]
            if tuple1[0]==SymbolTableEntry.ATTR_WRITE:
                return tuple1[1]
        return None
    
    # lambda adds a read for a pre declaration
    
    # immutable means no w or rw after a r
    # any r before : can be ignored
    # aggregate write means all writes within conditions
    # are mutually exclusive

    def is_immutable(self):
        sawread=False
        for (access_type, node_cross_reference) in self.usage:
            if access_type == self.ATTR_READ:
                sawread=True
            elif access_type == self.ATTR_WRITE or access_type == self.ATTR_READ_WRITE:
                if sawread:
                    return False
            elif access_type == self.ATTR_DECLARED:
                sawread=True
            elif access_type == self.ATTR_AMBIGUOUS:
                return False
        return True
        
    def is_declared(self):
        for (access_type, node_cross_reference) in self.usage:
            if access_type == self.ATTR_DECLARED:
                return True
        return False
        
    def is_declared(self):
        for (access_type, node_cross_reference) in self.usage:
            if access_type == self.ATTR_DECLARED:
                return True
        return False
        
    def is_set_unambiguously_across_if_blocks(self):
        sawread=False
        ifblockwrites = []
        for (access_type, node_cross_reference) in self.usage:
            if access_type == self.ATTR_READ:
                sawread=True
            elif access_type == self.ATTR_WRITE or access_type == self.ATTR_READ_WRITE:
                if not node_cross_reference.ConcurrencySafeContext():
                    return False
                if (node_cross_reference.if_stack):
                    for other in ifblockwrites:
                        if not self.mutually_exclusive_ifs(node_cross_reference.if_stack, other):
                            return False
                    ifblockwrites.append(node_cross_reference.if_stack)
                elif ifblockwrites:
                    return False
                elif not node_cross_reference.is_constant_write():
                    return False
                if sawread:
                    return False
            elif access_type == self.ATTR_DECLARED:
                sawread=True
            elif access_type == self.ATTR_AMBIGUOUS:
                return False

        if len(ifblockwrites)==0:
            return False
        return True

    def mutually_exclusive_ifs(self, ifblock1, ifblock2):
        shortest = min(len(ifblock1),len(ifblock2))
        for i in range(shortest):
            part1=ifblock1[i]
            part2 = ifblock2[i]
            if part1.if_frame != part2.if_frame:
                return False
            if part1.block_index != part2.block_index:
                return True
        return False
    
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
        
    def ConcurrencySafeContext(self):
        for node in self.ancestors:
            if isinstance(node, ast.For):
                return False
            if isinstance(node, ast.While):
                return False
            if isinstance(node, ast.With):
                return False
            if isinstance(node, ast.Try):
                return False
        return True
    def is_constant_write(self):
        if len(self.ancestors)<2:
            return False
        assigner = self.ancestors[-2]
        return self.is_constant(assigner.value)
        
    def is_constant(self, node):
        if sys.version_info >= (3, 9):
            if isinstance(node, ast.Constant):
                return True
        else:
            if isinstance(node, ast.Num):
                return True
            if isinstance(node, ast.Str):
                return True
            if isinstance(node, ast.Bytes):
                return True
            if isinstance(node, ast.Ellipsis):
                return True
            if isinstance(node, ast.NameConstant):
                return True
        return False

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
                if loopnode.orelse!=None and len(loopnode.orelse)>0:
                    self.bodies.append(loopnode.orelse)
                    self.blockframes.append(IfBlockFrame(len(self.blockframes),self))
                break
    
class IfBlockFrame:
    def __init__(self, block_index, if_frame):
        self.is_mutating_condition=False
        self.if_frame = if_frame
        self.block_index= block_index
        
