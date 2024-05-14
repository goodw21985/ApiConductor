import ast
from ast_transform import astor_fork

def fn():
    
    src="""
val +=             orchestrator._wait(orchestrator.search_email(a, _id='_C0'), '_C0')
"""
    past=ast.parse(src)
    code = astor_fork.to_source(past)
    return code
    
print(fn())