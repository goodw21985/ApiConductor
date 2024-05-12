import unittest

import ast
from ast_transform import astor_fork

from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import common
from unittest.mock import patch
import io

config = common.Config()
config.awaitable_functions = ["search_email", "search_teams", "search_meetings"]
config.module_blacklist = None




def walk_groups(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = analyzer2.critical_node_names
    crit = analyzer2.critical_nodes
    grps = analyzer2.concurrency_groups
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = astor_fork.to_source(c).strip()
            nodec = analyzer2.node_lookup[c]
            result = " ".join([named[item] for item in nodec.dependency])

            print(named[c] + " => " + gn + " used by (" + result + ")" + " = " + code)
        except Exception:
            pass

    print()

    for n in grps:
        result = " ".join([item.name for item in n.depends_on_group])
        resultn = " ".join([named[item] for item in n.grouped_critical_nodes])
        print(n.name + " <= (" + resultn + ") : uses " + result)

    print()


def walk_nodes(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = analyzer2.critical_node_names
    crit = analyzer2.critical_nodes
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = astor_fork.to_source(c).strip()
            print(gn + " = " + code)
        except Exception:
            pass
    for n in analyzer2.node_lookup.keys():
        nodec = analyzer2.node_lookup[n]
        if not nodec.dependency_visited:
            continue
        try:
            code = astor_fork.to_source(n).strip()
            result2 = " ".join([named[item] for item in nodec.dependency])
            print(nodec.assigned_concurrency_group.name + ": " + result2 + " " + code)
        except Exception:
            pass
    pass


class TestQRAnalyzerModule(unittest.TestCase):
    def get(self, code):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            print(code)
            print()

            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, config)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
            walk_groups(analyzer3)
            walk_nodes(analyzer3)
            rewrite= rewriter.Scan(tree, analyzer3)
            result = astor_fork.to_source(rewrite).strip()
            print('')
            print(result)
            result = mock_stdout.getvalue().strip()
            return result

##########################
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

        expected = """
import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _C1 = _C2 = _C3 = _return_value = a = n = None

    def _concurrent_G0():
        nonlocal _C0
        _C0 = orchestrator.search_teams(0, _id='_C0')

    def _concurrent_G1():
        nonlocal _C0, _C1, _C2, n
        n = _C0.Result
        _C1 = orchestrator.search_email(1, _id='_C1')
        _C2 = orchestrator.search_email(2, _id='_C2')

    def _concurrent_G2():
        nonlocal _C1, _C2, _C3, a
        _C3 = orchestrator.search_teams(a, _id='_C3')

    def _concurrent_G3():
        nonlocal _C3, _return_value, a, n
        if n == 3:
            a = _C1.Result
        else:
            a = _C2.Result
        _return_value = _C3.Result
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['_C1', '_C2'], _concurrent_G3: ['_C3']})
    return _return_value


orchestrator.Return(_program(orchestrator))"""


#ERRORS:
# 1. if statements needed in g1.      
# 4. else's are needed to detect incompletions.

        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
