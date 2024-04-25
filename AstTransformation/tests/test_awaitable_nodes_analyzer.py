import unittest

import ast

from ast_transform import awaitable_nodes_analyzer
from unittest.mock import patch
import io

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code = """
search_email(a,b,c)
"""

expected="""
"""

def walk(tree):
    pass
    
class TestAwaitableNodesModule(unittest.TestCase):
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_walk(self, mock_stdout):
        # Test your function here
        tree = ast.parse(source_code)
        t= awaitable_nodes_analyzer.Scan(tree, awaitable_functions)
        walk(t)
        result=mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()