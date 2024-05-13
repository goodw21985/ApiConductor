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
config.wrap_in_function_def =True


class TestRewriterModule(unittest.TestCase):
############
    def test_split(self):
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
        config.wrap_in_function_def =True

        self.check(source_code, validate)
###################
    def test_non_concurrent(self):
        source_code = """
n=None
for a in range(1):
    n=n or search_teams(a)
return n
"""


        expected="""
import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _return_value = n = None

    def _concurrent_G0():
        nonlocal _C0, _return_value, n
        n = None
        for a in range(1):
            n = n or 
            orchestrator._wait(orchestrator.search_teams(a, _id='_C0'), '_C0')
        _return_value = n
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))
"""
        config.wrap_in_function_def =False

        self.check(source_code, None, expected)
###################
    def test_critical_if_split(self):
        source_code = """
n=search_teams(0)
m = search_teams(n)
if n==3:
    a=search_email(1)
else:
    if m==3:
        a=search_email(2)
    else:
        a=search_email(3)
return search_teams(a)
"""
        expected="""
import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _C1 = _C2 = _C3 = _C4 = _C5 = _return_value = a = m = n = None

    def _concurrent_G0():
        nonlocal _C0
        _C0 = orchestrator.search_teams(0, _id='_C0')

    def _concurrent_G1():
        nonlocal _C0, _C1, _C2, n
        n = _C0.Result
        _C1 = orchestrator.search_teams(n, _id='_C1')
        if n == 3:
            _C2 = orchestrator.search_email(1, _id='_C2')

    def _concurrent_G2():
        nonlocal _C1, _C3, _C4, m
        m = _C1.Result
        if not n == 3 and m == 3:
            _C3 = orchestrator.search_email(2, _id='_C3')
        if not n == 3 and not m == 3:
            _C4 = orchestrator.search_email(3, _id='_C4')

    def _concurrent_G3():
        nonlocal _C5, a
        _C5 = orchestrator.search_teams(a, _id='_C5')

    def _concurrent_G4():
        nonlocal _C5, _return_value
        _return_value = _C5.Result

    def _concurrent_G_a():
        nonlocal _C2, _C3, _C4, a, m, n
        if n == 3:
            a = _C2.Result
        elif m == 3:
            a = _C3.Result
        else:
            a = _C4.Result
        orchestrator._complete('G_a')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['_C0'], _concurrent_G3: ['G_a'], _concurrent_G4: ['_C5'], _concurrent_G_a: [['_C1', '_C2', '_C3', '_C4']]})
    return _return_value


orchestrator.Return(_program(orchestrator))"""

        config.wrap_in_function_def =False

        self.check(source_code, None, expected)
   ###################
        
    def check(self, code, validate, expected=None):
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
        if validate!=None:
            verify = code_verification.CodeVerification(rewrite, config, validate)       
   
        if expected!=None:
            self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()