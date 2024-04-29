
import ast
from multiprocessing import Value
from ast_transform import astor

class VerificationVisitor(ast.NodeVisitor):


    # functionDef entry point if arguments != None
    def __init__(self, node, arguments=None):
        self.arguments = arguments      # arguments to this functionDef, or null
        self.assignments = {}           # all variables assigned to 
        self.statements = []            # all statements without assignments, or if or loops
        self.async_calls = set([])      # all calls to orchestrator functions
        self.names=set([])              # list of symbols used
        self.awaitednames=set([])       # list of symbols used with await
        self.async_names = set([])      # all variables that require await        
        self.globals=set([])            # list of symbols that are global
        self.initialized=set([])        # list of symbols set to None before anything else
        self.defs = {}                  # nodes of all functions defined
        self.children = {}              # child VerificationVisitor for each function defined
        if (arguments!=None):
            self.inDef=True
            for sub in node:
                self.visit(sub)
        else:
            self.inDef=False
            self.visit(node)

            for funcDefName in self.defs.keys():
                funcDef = self.defs[funcDefName]
                self.children[funcDefName] = VerificationVisitor(funcDef.body, funcDef.args)
     
    def visit_Await(self, node):
        if isinstance(node.value, ast.Name):
            if self.inDef:
                if node.value.id not in self.globals:
                    raise ValueError("symbol not global")
            self.awaitednames.add(node.value.id)
        else:
            raise ValueError("can only await ast.Name")
    
    def visit_Name(self, node):
        if node.id == "orchestrator":
            return
        if self.inDef:
            if node.id not in self.globals:
                raise ValueError("symbol not global")
            
        if node.id=="__3":
            pass
        self.names.add(node.id)
               
    def visit_Global(self, node):
        if not self.inDef:
            raise ValueError("global must be inside function def")
        for n in node.names:
            if n in self.names:
                raise ValueError("globals first")
            if n in self.awaitednames:
                raise ValueError("globals first")
            self.globals.add(n)
            
    def visit_Expr(self, node):
        self.statements.append(node)
        self.statement = node
        self.generic_visit(node)
            
          
    def visit_Assign(self, node):
        self.statement = node
        if isinstance(node.value, ast.Call):
            self.visit_Call(node.value)
            if self.is_orchestrator_call:
                symbol = node.targets[0].id
                self.awaitednames.add(symbol)
                self.assignments[symbol] = node.targets
                return

        if len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            id = node.targets[0].id
            initialized=False
            if isinstance(node.value, ast.Constant):
                if node.value.value==None:
                    id = node.targets[0].id
                    if (id not in self.names):
                        self.initialized.add(id)
                        initialized=True
            if not initialized:
                self.assignments[id] = node.targets
        else:
            raise ValueError("assignment to tuple")
        self.generic_visit(node)

    def visit_Call(self, node):
        self.is_orchestrator_call=False
        isAssignChild= False
        isExprChild= False
        if isinstance(self.statement, ast.Assign):
            isAssignChild = self.statement.value == node
        elif isinstance(self.statement, ast.Expr):
            isExprChild = self.statement.value == node
            
        if (isinstance(node.func, ast.Attribute) 
            and isinstance(node.func.value, ast.Name) 
            and node.func.value.id=="orchestrator"):

            name = node.func.attr
            self.async_calls.add(name)
            
            if not isAssignChild and not isExprChild:
                raise ValueError("orchestrator functions must be in assign or expr statements")
            
            for arg in node.args:
                if not isinstance(arg, ast.Name) and not isinstance(arg, ast.Constant):
                    raise ValueError("orchestrator function arguments must be ast.Name")
            for kw in node.keywords:
                if not isinstance(kw.value, ast.Name) and not isinstance(kw.value, ast.Constant):
                    raise ValueError("orchestrator function arguments must be ast.Name")

            if isAssignChild:
                if len(self.statement.targets)==1:
                    target = self.statement.targets[0]
                    if isinstance(target, ast.Name):
                        self.async_names.add(target.id)
                        self.is_orchestrator_call=True
                    else:
                        raise ValueError("orchestrator values must be set to name")
                else:
                    raise ValueError("orchestrator values cannot be set to tuple")
                    
        self.generic_visit(node)
            
    def visit_FunctionDef(self, node):
        self.defs[node.name] = node
        if self.inDef:
            raise ValueError("no recursive function definitions")

    def checkawait(self):
        names=set(self.names)                     # list of symbols used
        awaitednames=set(self.awaitednames)       # list of symbols used with await
        async_names = set( self.async_names)      # all variables that require await        
        for childname in self.children:
            child = self.children[childname]
            names |= child.names
            awaitednames |= child.awaitednames
            async_names |= child.async_names
        for name in names:
            if name in async_names:
                raise ValueError("symbol is missing await")
        for name in awaitednames:
            if name not in async_names:
                raise ValueError("symbol should not be awaited")

    def validateAssignment(self, isExpected, expected):
        if (expected in self.assignments.keys()):
            if not isExpected:
                raise ValueError("assignment seen where not expected")
        else:
            if isExpected:
                raise ValueError("assignment not seen where expected")
        
    def validateFunction(self, isExpected, expected):
        if (expected in self.async_calls):
            if not isExpected:
                raise ValueError("function seen where not expected")
        else:
            if isExpected:
                raise ValueError("function not seen where expected")
        

    def validate(self, isExpected, expected):
        for item in expected:
            if isinstance(item, list):
                for sub in item:
                    self.validateFunction(isExpected, sub)
            else:
                self.validateAssignment(isExpected, item)
            
    def validateAll(self, expected):
        for group in expected.keys():
            child = self
            if group!=...:
                child = self.children[group]
            for group2 in expected.keys():
                child2 = self
                if group2!=...:
                    child2 = self.children[group2]
                child2.validate(child==child2, expected[group])

class CodeVerification:
    def __init__(self,tree, validate):
        self.root = VerificationVisitor(tree)
        self.root.checkawait()
        self.root.validateAll(validate)
        
        
            
            
        
        