import unittest

import ast

from ast_transform import dependency_analyzer
from ast_transform import awaitable_nodes_analyzer
from ast_transform import variables_analyzer
from unittest.mock import patch
import io

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code = """
f=1
f=2
a=3*d+e*f
x=search_email(a,b,c)
"""

expected="""
"""

def walk(tree):
    pass

class TestDependencyAnalyzerModule(unittest.TestCase):
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_walk(self, mock_stdout):
        # Test your function here
        tree = ast.parse(source_code)
        analyzer1 = variables_analyzer.Scan(tree, awaitable_functions)
        analyzer2 = dependency_analyzer.Scan(tree, analyzer1)

        result=mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()