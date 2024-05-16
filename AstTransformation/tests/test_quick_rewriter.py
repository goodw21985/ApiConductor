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
config.awaitable_functions = ["search_email", "search_teams", "search_meetings", "create_dict", "wrap_string"]
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
processed_values = {search_email(item) for item in range(10) if item % 2 == 0}
return processed_values
"""

        expected = """
processed_values = {search_email(item) for item in range(10) if item % 2 == 0}
return processed_values


C0 => G0 used by (C1) = {search_email(item) for item in range(10) if item % 2 == 0}
C1 => G1 used by () = return processed_values

G0 <= (C0) : uses 
G1 <= (C1) : uses G0

G0 = {search_email(item) for item in range(10) if item % 2 == 0}
G1 = return processed_values
G1: C1 processed_values = {search_email(item) for item in range(10) if item % 2 == 0}
G0: C1 {search_email(item) for item in range(10) if item % 2 == 0}
G0: C0 for item in range(10) if item % 2 == 0
G0: C0 item
G0: C0 range(10)
G0: C0 range
G0: C0 10
G0: C0 item % 2 == 0
G0: C0 item % 2
G0: C0 item
G0: C0 2
G0: C0 0
G0: C0 search_email(item)
G0: C0 search_email
G0: C0 item
G1:  return processed_values
G1: C1 processed_values

import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _comp_C0 = _return_value = item = processed_values = None

    def _concurrent_G0():
        nonlocal _comp_C0, item
        _comp_C0 = [orchestrator.search_email(item, _id=orchestrator._create_id('_C0', _concurrent_G_C0)) for item in range(10) if item % 2 == 0]
        orchestrator._complete('_comp_C0')

    def _concurrent_G1():
        nonlocal _comp_C0, _return_value, processed_values
        processed_values = _C0.Result
        _return_value = processed_values

    def _concurrent_G_C0():
        nonlocal _C0, _comp_C0
        _C0 = orchestrator._create_task({item.Result for item in _comp_C0})
        orchestrator._complete('_C0')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G_C0: ['_comp_C0']})
    return _return_value


orchestrator.Return(_program(orchestrator))"""

        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
