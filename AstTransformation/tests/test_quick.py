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
config.use_async=False
config.wrap_in_function_def =False
config.log=True

# Primarily used as a debugging playground, but the test will pass as
# long as there are no exceptions

source_code = """
n=search_meetings()
if n>3:
    a=search_email()
else:
    a=search_teams()

return a
"""


class TestQuickModule(unittest.TestCase):
    def test_split(self):
         result = self.get(source_code)
        
    def get(self, code):
            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, config)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            walk(analyzer2)
   
    def check(self, code):
        tree = ast.parse(code)
        if config.wrap_in_function_def:
            tree.body = tree.body[0].body
        analyzer1 = variables_analyzer.Scan(tree, config)
        analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
        analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
        rewrite= rewriter.Scan(tree, analyzer3)
        result = astor_fork.to_source(rewrite).strip()
        print(result)
        with open("C:/repos/llmPython/LLmModule/test2.py", 'w') as file:
            file.write(result)  

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
        
if __name__ == '__main__':
    unittest.main()