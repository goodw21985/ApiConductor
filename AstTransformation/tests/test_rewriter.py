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

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code = """
q=3
a=search_email(q)
sum=a+a2
sum+=q
sum2=sum+3
b=search_email(sum)  or search_teams(sum2)
c=b
return c
"""

expected="""
q = 3
a = search_email(q)
sum = a + a2
sum += q
sum2 = sum + 3
b = search_email(sum) or search_teams(sum2)
c = b
return c"""

class TestRewriterModule(unittest.TestCase):
    def test_split(self):
        result=self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
        
    def get(self, code):
            print(code)
            print()

            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, awaitable_functions)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
            tree = rewriter.Scan(tree, analyzer3)
            return astor.to_source(tree).strip()
        
if __name__ == '__main__':
    unittest.main()