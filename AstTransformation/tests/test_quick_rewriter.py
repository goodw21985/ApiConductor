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
inputs = {'a': 10, 'b': 20}
result_dict = create_dict(inputs['a'], inputs['b'])
result_dict['c']=30
return wrap_string(result_dict)


C0 => G0 used by (C1) = create_dict(inputs['a'], inputs['b'])
C2 => G1 used by () = return wrap_string(result_dict)

G0 <= (C0) : uses 
G1 <= (C2) : uses G0

G0 = create_dict(inputs['a'], inputs['b'])
G1 = return wrap_string(result_dict)
G0: C0 inputs = {'a': 10, 'b': 20}
G0: C0 {'a': 10, 'b': 20}
G0: C0 \"\"\"a\"\"\"
G0: C0 \"\"\"b\"\"\"
G0: C0 10
G0: C0 20
G1: C1 result_dict = create_dict(inputs['a'], inputs['b'])
G0: C1 create_dict(inputs['a'], inputs['b'])
G0: C0 create_dict
G0: C0 inputs['a']
G0: C0 inputs
G0: C0 \"\"\"a\"\"\"
G0: C0 inputs['b']
G0: C0 inputs
G0: C0 \"\"\"b\"\"\"
G1:  return wrap_string(result_dict)
G1: C2 wrap_string(result_dict)
G1: C1 wrap_string
G1: C1 result_dict

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

        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
