import unittest
import io
import sys
import itertools

import ast
from ast_transform import astor_fork
from ast_transform import transform
from ast_transform import scope_analyzer
from ast_transform import common

class Mock():

    def __init__(self, library, target, inputs):

        self.awaitable_functions={}

        self.inputs_code = inputs
        self.inputs_ast = ast.parse(self.inputs_code).body
        self.parse_inputs(self.inputs_ast)
        self.library_code=library
        self.library_ast = ast.parse(self.library_code)
        self.target_code=target
        self.target_ast = ast.parse(self.target_code)
        self.build_awaitable_functions_class()

        config = common.Config()
        config.exposed_function=None
        config.awaitable_functions=self.awaitable_functions
        config.module_blacklist=None
        config.statement_whitelist=None
        config.wrap_in_function_def =False
        config.statement_whitelist={'if','for','return', 'pass'}

        self.transform = transform.Transform(config).modify_code(target)
        
        self.build_module()
        self.new_code =astor_fork.to_source(self.module)
        
        self.run_normal()
        self.run_new_code()

    def parse_inputs(self, inputs):
        self.variables = {}
        for statement in inputs:
            if isinstance(statement, ast.Assign):
                name = statement.targets[0].id
                listval = statement.value
                list2= []
                if isinstance(listval, ast.List):
                    for el in listval.elts:
                        list2.append(el.value)
                if not list2:
                    raise ValueError("could not find list of constants")
                self.variables[name]=list2
                   
        
    def run_normal(self):
        self.code1 = self.wrap_code_snippet(self.library_code+"\n"+self.target_code)
        self.capture1=self.multi_capture(self.code1)
        print(self.capture1)
        print()
        print()
        
    def run_new_code(self):
        self.capture2=self.multi_capture(self.new_code, mod=True)
        print(self.capture2)
        print()
        print()
        
    def build_module(self):
        # Create an AST Module to house the class
        statements = []
        
        # => import ast_transform.orchestrator
        import_node = ast.ImportFrom(
            module='ast_transform',   # The module to import from
            names=[ast.alias(name='test_orchestrator', asname=None)],  # The names to import
            level=0  # Absolute import
        )
        statements.append(import_node)
        
        target_node = ast.Name(id='orchestrator', ctx=ast.Store())  # Variable to assign to

        # => class MockOrchestrator(orchestrator.Orchestrator):

        statements.append(self.derived_class)

        

        # orchestrator = MockOrchestrator()
        
        call_node = ast.Call(
            func=ast.Name(id='MockOrchestrator', ctx=ast.Load()), 
            args=[],  
            keywords=[]  
        )

        target_node = ast.Name(id='orchestrator', ctx=ast.Store())  # Variable to assign to

        assign_node = ast.Assign(
            targets=[target_node],  # List of targets, in this case just one variable
            value=call_node  # The right-hand side call expression
        )
        
        statements.append(assign_node)
        
        for statement in self.transform.body:
            if isinstance(statement,ast.FunctionDef):
                if statement.name == "_program":
                    statement = self.fix_program(statement)
                statements.append(statement)
            if isinstance(statement,ast.Expr):
                statements.append(statement)
        
        self.module= ast.Module(body=statements, type_ignores=[])


    def fix_program(self, node):
        statements=[]
        for test_globals in self.variables.keys():
            assign_node = ast.Assign(
                targets=[ast.Name(id=test_globals, ctx=ast.Store())],  # List of targets, in this case just one variable
                value=ast.Name(id="_init_"+test_globals, ctx=ast.Load()) # The right-hand side call expression
            )
            
            statements.append(assign_node)
            
            # test_call = ast.Call(func=ast.Name(id='print', ctx=ast.Load),
            #                            args=[ast.Name(id ="_init_"+test_globals, ctx=ast.Load())
            #                                  ], keywords=[])
            # 
            # test_statement = ast.Expr(test_call)
            # statements.append(test_statement)
            
            
        for statement in node.body:
            statements.append(statement)
            
        return ast.FunctionDef(name=node.name, args=node.args, body=statements, returns = node.returns,decorator_list=node.decorator_list)

    def wrap_return(self, node):
        if node.value is None:  # Check if the return statement returns something
            return node
        # Wrap the return value in self.Task(id, original_return_value)
        new_return_value = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='self', ctx=ast.Load()),
                attr='start_task',
                ctx=ast.Load()
            ),
            args=[
                ast.Name(id='_id', ctx=ast.Load()),
                node.value  # original return value
            ],
            keywords=[]
        )
        return ast.Return(new_return_value)
        
    def build_awaitable_functions_class(self):
        function_defs=[]
        for defn in self.library_ast.body:         
            self.awaitable_functions[defn.name]=[]
            # def search_email(a=0, b=0):
            # return str(a)+ "1"
            # =>
            # def search_email(self, a=0, b=0, _id=None):
            # return self.task(_id, str(a)+ "1")
            # Create an ast.Name node for 'self'
            self_node = ast.Name(id='self', ctx=ast.Load())
            
            args = defn.args.args[:]
            defaults = defn.args.defaults[:]

            # Insert 'self' at the beginning of the args list
            args.insert(0, self_node)
            
            defaults.append(ast.Constant(None))
            args.append(ast.Name(id='_id', ctx=ast.Load()))

            statements = []
            for statement in defn.body:
                if isinstance(statement, ast.Return):
                    statements.append(self.wrap_return(statement))
                else:
                    statements.append(statement)

            arguments = ast.arguments(
                posonlyargs=[],  
                args=args, 
                vararg=None, 
                kwonlyargs=[],  
                kw_defaults=[],  
                kwarg=None,  
                defaults=defaults
            )
    
            new_function_def = ast.FunctionDef(
                name=defn.name,
                args=arguments,
                
                body=statements, 
                decorator_list=[],
                returns=None  
            )
            
            function_defs.append(new_function_def)
            
        self.derived_class = ast.ClassDef(
            name='MockOrchestrator',
            bases=[
                ast.Attribute(
                    value=ast.Name(id='test_orchestrator', ctx=ast.Load()), 
                    attr='Orchestrator', 
                    ctx=ast.Load()
                )
            ],
            keywords=[],
            body=function_defs,
            decorator_list=[]
        )

    def wrap_code_snippet(self, code_snippet):
        # Extract the existing code snippet
        lines = code_snippet.split("\n")

        # Add the function definition line
        modified_lines = ["def fn():"] + ["    " + line for line in lines]

        # Join the modified lines back into a single string
        modified_code = "\n".join(modified_lines)
        
        modified_code+="\nprint(fn())"

        return modified_code
    
    def multi_capture(self, code_string, mod=False):
        result={}

        if self.variables:
            keys, lists = zip(*self.variables.items())
    
            # Generate all combinations using itertools.product
            for combination in itertools.product(*lists):
                # Create a dictionary of the current combination with corresponding keys
                original_dict = dict(zip(keys, combination))
            
                if mod:
                    combination_dict = {'_init_' + key: value for key, value in original_dict.items()} 
                else:
                    combination_dict=original_dict

                id = ",".join(f"{key}={value}" for key, value in sorted(original_dict.items()))
        
                # Call the delegate function with the combination dictionary
                result[id] = self.capture(code_string, combination_dict)
        else:
            result["_"] = self.capture(code_string, {})
            

        return result
    
    def capture(self, code_string, combination_dict):
        globals_dict = combination_dict.copy()
        locals_dict = {}

        output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output
        try:
            exec(code_string, globals_dict, locals_dict)
        finally:
            sys.stdout = original_stdout
        captured_output = output.getvalue()
        output.close()        
        return captured_output
    
