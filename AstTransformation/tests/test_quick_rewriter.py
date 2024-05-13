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
n=None
for a in range(1):
    n=n or search_teams(a)
return n
"""

        expected = """
n=None
for a in range(1):
    n=n or search_teams(a)
return n


C1 => G0 used by () = return n

G0 <= (C1) : uses 

G0 = return n
G0: C1 n = None
G0: C1 None
G0: C1 n = n or search_teams(a)
G0: C1 n or search_teams(a)
G0: C1 n
G0: C1 search_teams(a)
G0: C0 search_teams
G0: C0 a
G0:  return n
G0: C1 n

import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _return_value = n = None

    def _concurrent_G0():
        nonlocal _C0, _return_value, n
        n = None
        for a in range(1):
            n = n or 
            orchestrator._wait(orchestrator.search_teams(a, _id='_C0'))
        _return_value = n
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))"""


        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
