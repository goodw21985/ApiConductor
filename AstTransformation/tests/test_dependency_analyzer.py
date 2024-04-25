from tkinter import EXCEPTION
import unittest

import ast
from ast_transform import astor

from ast_transform import dependency_analyzer
from ast_transform import awaitable_nodes_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from unittest.mock import patch
import io

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code = """
a=search_email(q)
x=search_email(a)
return x
"""

expected="""
C0 = search_email(q)
C1 = search_email(a)
C2 = return x
* C0 C1 search_email(q)
C0 search_email
C0 q
* C1 C2 search_email(a)
C1 search_email
C1 a
C1 a = search_email(q)
* C2 return x
C2 x
C2 x = search_email(a)"""

def walk(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = {}
    crit = analyzer2.critical_nodes
    num = 0
    for c in crit:
        named[c]= "C"+str(num)
        num+=1
        try:
            code = astor.to_source(c).strip()
            print(named[c] + " = "+code)
        except EXCEPTION:
            pass
    for n in analyzer2.nodelookup.keys():
        nodec = analyzer2.nodelookup[n]
        try:
            code = astor.to_source(n).strip()
            result = ' '.join([named[item] for item in nodec.dependency])
            if n in crit:
                result = "* "+result
            print(result+" "+code)
        except Exception:
            pass
    pass

class TestDependencyAnalyzerModule(unittest.TestCase):
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_walk(self, mock_stdout):
        tree = ast.parse(source_code)
        analyzer1 = variables_analyzer.Scan(tree, awaitable_functions)
        analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
        walk(analyzer2)
        result=mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()