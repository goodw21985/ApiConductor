from tkinter import EXCEPTION
import unittest

import ast
from ast_transform import astor_fork

from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import common
from unittest.mock import patch
import io

awaitable_functions = {"search_email":[], "search_teams":[], "search_meetings":[]}




def walk(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = analyzer2.critical_node_names
    crit = analyzer2.critical_nodes
    for n in analyzer2.node_lookup.keys():
        nodec = analyzer2.node_lookup[n]
        try:
            if n in crit:
                code = astor_fork.to_source(n).strip()
                result = " ".join([named[item] for item in nodec.dependency])
                result = named[n] + " => " + result
                print(result + " " + code)
        except Exception:
            pass
    pass


config = common.Config()
config.awaitable_functions = {"search_email":[], "search_teams":[], "search_meetings":[]}
config.module_blacklist = None
config.statement_whitelist={'if', 'return','pass'}
config.function_blacklist = {'open', 'eval', 'exec', 'compile', '__import__'}
 

class TestDependencyAnalyzerModule(unittest.TestCase):
    def get(self, code):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, config)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            walk(analyzer2)
            result = mock_stdout.getvalue().strip()
            return result

##################################
    def test_if_block(self):
        source_code = """
n=search_meetings()
if n>3:
    a=search_email()
else:
    a=search_teams()

return a
"""

        expected = """
C0 => C1 C2 C3 search_meetings()
C1 => C3 search_email()
C2 => C3 search_teams()
C3 =>  return a"""
        result = self.get(source_code)
        self.assertEqual(result, expected.strip())

##################################
    def test_ambiguous(self):
        source_code = """
a=[search_email(9,0), 2]
return search_email(a[1])
"""

        expected = """
C0 => C1 search_email(9, 0)
C2 =>  return search_email(a[1])
C1 => C2 search_email(a[1])"""
        result = self.get(source_code)
        self.assertEqual(result, expected.strip())

##################################
    def test_simple(self):
        source_code = """
a=search_email(q)
x=search_email(a)
return x
"""

        expected = """
C0 => C1 search_email(q)
C1 => C2 search_email(a)
C2 =>  return x"""
        result = self.get(source_code)
        self.assertEqual(result, expected.strip())

##################################

    def test_parallel(self):
        source_code2 = """
q=3
a=search_email(q)
sum=a*3
sum+=q
b=search_email(sum)  or search_teams(sum+1)
return b
"""

        expected2 = """
C0 => C1 C2 search_email(q)
C1 => C3 search_email(sum)
C2 => C3 search_teams(sum + 1)
C3 =>  return b"""
 
        result = self.get(source_code2)
        print(result)
        self.assertEqual(result, expected2.strip())

 #############################


if __name__ == "__main__":
    unittest.main()
