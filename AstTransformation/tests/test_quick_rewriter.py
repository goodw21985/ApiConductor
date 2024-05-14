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
y=None
a=search_email(x)
print(a)
if (a<3):
    print("A lt 3")
    y=search_email(a+5)
elif a>7:
    print("A gt 7")
    y=search_email(a+10)
return y"""

        expected = """
y=None
a=search_email(x)
print(a)
if (a<3):
    print("A lt 3")
    y=search_email(a+5)
elif a>7:
    print("A gt 7")
    y=search_email(a+10)
return y

C0 => G0 used by (C1 C2) = search_email(x)
C1 => G1 used by (C3) = search_email(a + 5)
C2 => G1 used by (C3) = search_email(a + 10)
C3 => G2 used by () = return y

G0 <= (C0) : uses 
G1 <= (C1 C2) : uses G0
G2 <= (C3) : uses G1 G_y
G_y <= () : uses G1

G0 = search_email(x)
G1 = search_email(a + 5)
G1 = search_email(a + 10)
G2 = return y
G2: C3 y = None
G2: C3 None
G1: C1 C2 a = search_email(x)
G0: C1 C2 search_email(x)
G0: C0 search_email
G0: C0 x
G1: C1 C2 (a < 3)
G1: C1 C2 a
G1: C1 C2 3
G_y: C3 y = search_email(a + 5)
G1: C3 search_email(a + 5)
G1: C1 search_email
G1: C1 a + 5
G1: C1 a
G1: C1 5
G_y: C3 y = search_email(a + 10)
G1: C3 search_email(a + 10)
G1: C2 search_email
G1: C2 a + 10
G1: C2 a
G1: C2 10
G2:  return y
G2: C3 y
G1: C2 (a > 7)
G1: C2 a
G1: C2 7

import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _1 = _2 = _C0 = _C1 = _C2 = _return_value = a = y = None

    def _concurrent_G0():
        nonlocal _C0, x
        _C0 = orchestrator.search_email(x, _id='_C0')

    def _concurrent_G1():
        nonlocal _1, _2, _C0, _C1, _C2, a
        a = _C0.Result
        _1 = a + 5
        _2 = a + 10
        if not (a < 3 or not a < 3 and a > 7):
            orchestrator._complete('_C2')
        if a < 3:
            _C1 = orchestrator.search_email(_1, _id='_C1')
        if not a < 3 and a > 7:
            _C2 = orchestrator.search_email(_2, _id='_C2')

    def _concurrent_G2():
        nonlocal _return_value, y
        _ = None
        _return_value = y

    def _concurrent_G_y():
        nonlocal _C1, _C2, a, y
        print(a)
        if a < 3:
            print('A lt 3')
            y = _C1.Result
        elif a > 7:
            print('A gt 7')
            y = _C2.Result
        orchestrator._complete('G_y')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['G_y'], _concurrent_G_y: [['_C1', '_C2']]})
    return _return_value


orchestrator.Return(_program(orchestrator))"""


        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
