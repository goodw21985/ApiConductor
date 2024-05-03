import ast
from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import code_verification
from . import astor_fork

config = scope_analyzer.Config()
config.awaitable_functions = ["search_email", "search_teams", "search_meetings"]
config.module_blacklist = None
config.use_async = False
config.wrap_in_function_def = True


def modify_code(code, config):
    if config.wrapInFunctionDef:
        wrapped_code = wrap_code_snippet(code)
        tree = ast.parse(wrapped_code)
        tree.body = tree.body[0].body
        rresult = astor_fork.to_source(tree).strip()
        print(rresult)
    else:
        tree = ast.parse(wrapped_code)

    analyzer1 = variables_analyzer.Scan(tree, config)
    analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
    analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
    rewrite = rewriter.Scan(tree, analyzer3)
    return rewrite


def wrap_code_snippet(code_snippet):
    # Extract the existing code snippet
    lines = code_snippet.split("\n")

    # Add the function definition line
    modified_lines = ["def fn():"] + ["    " + line for line in lines]

    # Join the modified lines back into a single string
    modified_code = "\n".join(modified_lines)

    return modified_code
