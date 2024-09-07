import ast

def fn():
    
    src="""
val +=             orchestrator._wait(orchestrator.search_email(a, _id='_C0'), '_C0')
"""
    past=ast.parse(src)
    code = ast.unparse(past).strip()
    return code
    
print(fn())