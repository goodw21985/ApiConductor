import unittest

import ast
from ast_transform import astor

from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from unittest.mock import patch
import io

import code_verification

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code = """
pass
q=3
a=search_email(q,0)
sum=a+a2
sum+=q
sum2=sum+3
b=search_email(sum+1)  or search_teams(b=sum2+1)
c=b
return c
"""

expected="""
def _concurrent_G0():
    global q
    pass
    q = 3


def _concurrent_start_G0():
    global __1
    __1 = orchestrator.search_email(q, 0)


def _concurrent_G1():
    global __2
    global __4
    global a
    global a2
    global q
    global sum
    global sum2
    a = await __1
    sum = a + a2
    sum += q
    sum2 = sum + 3
    __2 = sum + 1
    __4 = sum2 + 1


def _concurrent_start_G1():
    global __3
    global __5
    __3 = orchestrator.search_email(__2)
    __5 = orchestrator.search_teams(b=__4)


__2 = None
__4 = None
a = None
a2 = None
b = None
c = None
q = None
sum = None
sum2 = None
b = await __3 or await __5
c = b
orchestrator.Return(c)"""

class TestRewriterModule(unittest.TestCase):
    def test_split(self):
        rewrite=self.get(source_code)
        result = astor.to_source(rewrite).strip()
        print(result)

        verify = code_verification.CodeVerification(rewrite)
        
        self.assertEqual(result.strip(), expected.strip())
        
    def get(self, code):
        print(code)
        print()

        tree = ast.parse(code)
            
        analyzer1 = variables_analyzer.Scan(tree, awaitable_functions)
        analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
        analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
        rewrite= rewriter.Scan(tree, analyzer3)
        return rewrite
        
if __name__ == '__main__':
    unittest.main()