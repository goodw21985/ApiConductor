import ast
from . import astor
def modify_code(original_code, statement_to_add):
    # Parse the original code string into an AST
    tree = ast.parse(original_code)

    # Create a new statement AST node from the provided statement string
    new_statement = ast.parse(statement_to_add).body[0]

    # Insert the new statement at the beginning of the original AST body
    tree.body.insert(0, new_statement)

    # Convert the modified AST back into a code string
    modified_code = astor.to_source(tree)

    return modified_code
