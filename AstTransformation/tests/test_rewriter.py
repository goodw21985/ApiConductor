import unittest

import ast
from ast_transform import astor_fork

from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import common
from ast_transform import code_verification
from unittest.mock import patch
import io

config = common.Config()
config.awaitable_functions= ["search_email", "search_teams","search_meetings"]
config.module_blacklist=None
config.wrap_in_function_def =True

source_code = """
def fn():
    pass
    q=3
    a=search_email(q,0)
    sum=str(a)+'j'
    sum += str(q)
    sum2=sum + "q"
    b=search_meetings(sum+"a") + search_teams(b=sum2+"b")
    c=b
    return c
"""


validate={"_concurrent_G0": ["q", "_C0", ["search_email"]],
   "_concurrent_G1": ["a", "sum", "sum2", "_1", "_2", "_C1", "_C2",["search_meetings", "search_teams"]],
   "_concurrent_G2": ["b","c","_return_value"],
   }

class TestRewriterModule(unittest.TestCase):
    def test_split(self):
        self.check(source_code, validate)
        
        
    def check(self, code, validate):
        tree = ast.parse(code)
        if config.wrap_in_function_def:
            tree.body = tree.body[0].body
        analyzer1 = variables_analyzer.Scan(tree, config)
        analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
        analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
        rewrite= rewriter.Scan(tree, analyzer3)
        result = astor_fork.to_source(rewrite).strip()
        print(result)
        #
        with open("C:/repos/llmPython/LLmModule/test.py", 'w') as file:
            file.write(result)  
        verify = code_verification.CodeVerification(rewrite, config, validate)       
        
if __name__ == '__main__':
    unittest.main()