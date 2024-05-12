import unittest

import ast
from ast_transform import astor_fork

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

# G0 <= (C0) : uses 
# G1 <= (C1 C2) : uses G0
# G_a <= () uses G1
# G2 <= (C3) : uses G*
# G3 <= (C4) : uses G2

# n.grouped_critical_nodes for G_a is empty
# n.depends_on_group for G_a is now G1
# n.depends_on_group for G2 is now G_a instead of G1
    
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


class TestQAnalyzerModule(unittest.TestCase):
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
            result = mock_stdout.getvalue().strip()
            return result

##########################
    def test_critical_if_split(self):
        source_code = """
n=search_teams(0)
if n==3:
    a=search_email(1)
else:
    a=search_email(2)

return search_teams(a)
"""

        expected = """
n=search_teams(0)
if n==3:
    a=search_email(1)
else:
    a=search_email(2)

return search_teams(a)


C0 => G0 used by (C1 C2) = search_teams(0)
C1 => G1 used by (C3) = search_email(1)
C2 => G1 used by (C3) = search_email(2)
C3 => G2 used by (C4) = search_teams(a)
C4 => G3 used by () = return search_teams(a)

G0 <= (C0) : uses 
G1 <= (C1 C2) : uses G0
G2 <= (C3) : uses G1 G_a
G3 <= (C4) : uses G2
G_a <= () : uses G1

G0 = search_teams(0)
G1 = search_email(1)
G1 = search_email(2)
G2 = search_teams(a)
G3 = return search_teams(a)
G1: C1 C2 n = search_teams(0)
G0: C1 C2 search_teams(0)
G0: C0 search_teams
G0: C0 0
G1: C1 C2 (n == 3)
G1: C1 C2 n
G1: C1 C2 3
G_a: C3 a = search_email(1)
G1: C3 search_email(1)
G1: C1 search_email
G1: C1 1
G_a: C3 a = search_email(2)
G1: C3 search_email(2)
G1: C2 search_email
G1: C2 2
G3:  return search_teams(a)
G2: C4 search_teams(a)
G2: C3 search_teams
G2: C3 a"""

        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()
