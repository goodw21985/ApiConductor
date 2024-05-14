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
        result = " ".join(sorted([item.name for item in n.depends_on_group]))
        resultn = " ".join(sorted([named[item] for item in n.grouped_critical_nodes]))
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
a=search_email(x)
k=0
if (a<3):
    r=k
    k+=4
    print(k)
    b=search_teams(k)
return b
"""

        expected = """
a=search_email(x)
k=0
if (a<3):
    r=k
    k+=4
    print(k)
    b=search_teams(k)
return b


C0 => G0 used by (C1 C2) = search_email(x)
C2 => G1 used by () = return b

G0 <= (C0) : uses 
G1 <= (C2) : uses G0

G0 = search_email(x)
G1 = return b
G1: C1 C2 a = search_email(x)
G0: C1 C2 search_email(x)
G0: C0 search_email
G0: C0 x
G1: C1 k = 0
G1: C1 0
G1: C1 k += 4
G1: C1 k
G1: C1 4
G1: C2 b = search_teams(k)
G1: C2 search_teams(k)
G1: C1 search_teams
G1: C1 k
G1:  return b
G1: C2 b
G1: C1 C2 (a < 3)
G1: C1 C2 a
G1: C1 C2 3

import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _C1 = _return_value = a = b = k = r = None

    def _concurrent_G0():
        nonlocal _C0, x
        _C0 = orchestrator.search_email(x, _id='_C0')

    def _concurrent_G1():
        nonlocal _C0, _C1, _return_value, a, b, k, r
        a = _C0.Result
        k = 0
        if a < 3:
            r = k
            k += 4
            print(k)
            b = orchestrator._wait(orchestrator.search_teams(k, _id='_C1'), '_C1')
        _return_value = b
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0']})
    return _return_value


orchestrator.Return(_program(orchestrator))"""


        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
