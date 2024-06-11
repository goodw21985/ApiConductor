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
config.awaitable_functions = {"search_email":['text','take','sort','reverse'], "search_teams":[], "search_meetings":[], "create_dict":[], "wrap_string":[]}
config.exposed_functions={'now'}
config.module_blacklist=None
config.use_async=False
config.wrap_in_function_def =True
config.statement_whitelist={'if','for','return', 'pass'}


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
            n = n or orchestrator._wait(orchestrator.search_teams(a, _id='_C0'), '_C0')
        _return_value = n
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))
"""
        config.wrap_in_function_def =False

        self.check(source_code, None, expected)
##########################
    def test_mutation_split(self):
        source_code = """
inputs = {'a': 10, 'b': 20}
result_dict = create_dict(inputs['a'], inputs['b'])
result_dict['c']=30
return wrap_string(result_dict)
"""

        expected = """
import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _1 = _2 = _C0 = _C1 = _return_value = inputs = result_dict = None

    def _concurrent_G0():
        nonlocal _1, _2, _C0, inputs
        inputs = {'a': 10, 'b': 20}
        _1 = inputs['a']
        _2 = inputs['b']
        _C0 = orchestrator.create_dict(_1, _2, _id='_C0')

    def _concurrent_G1():
        nonlocal _C0, _C1, _return_value, inputs, result_dict
        result_dict = _C0.Result
        result_dict['c'] = 30
        _return_value = orchestrator._wait(orchestrator.wrap_string(result_dict, _id='_C1'), '_C1')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0']})
    return _return_value


orchestrator.Return(_program(orchestrator))"""

        config.wrap_in_function_def =False

        self.check(source_code, None, expected)
##########################
    def test_exposed_fn(self):
        source_code = """
a=now(3,4,a=5,b=search_email(3))
"""

        expected = """
import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _return_value = a = None

    def _concurrent_G0():
        nonlocal _C0
        _C0 = orchestrator.search_email(3, _id='_C0')

    def _concurrent_G1():
        nonlocal _C0, a
        a = orchestrator.now(3, 4, a=5, b=_C0.Result)
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0']})
    return _return_value


orchestrator.Return(_program(orchestrator))"""

        config.wrap_in_function_def =False

        self.check(source_code, None, expected)
##########################
    def test_no_return(self):
        source_code = """
search_email(take=1, sort='sent', reverse=True)"""
        expected = """
import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _return_value = None

    def _concurrent_G0():
        nonlocal _C0
        _C0 = orchestrator.search_email(take=1, sort='sent', reverse=True, _id='_C0')
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))"""

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
        nonlocal _C2, _C3, _C4, _C5, a
        _C5 = orchestrator.search_teams(a, _id='_C5')

    def _concurrent_G4():
        nonlocal _C5, _return_value, a, m, n
        if n == 3:
            a = _C2.Result
        elif m == 3:
            a = _C3.Result
        else:
            a = _C4.Result
        _return_value = _C5.Result

    def _concurrent_G_a():
        orchestrator._complete('G_a')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['_C0'], _concurrent_G3: ['G_a', '_C0'], _concurrent_G4: ['_C5'], _concurrent_G_a: [['_C2', '_C3', '_C4']]})
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
        if validate!=None:
            verify = code_verification.CodeVerification(rewrite, config, validate)       
   
        if expected!=None:
            self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()