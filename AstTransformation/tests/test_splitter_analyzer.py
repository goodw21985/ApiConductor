import unittest

import ast

from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import common
from unittest.mock import patch
import io

config = common.Config()
config.awaitable_functions = {"search_email":[], "search_teams":[], "search_meetings":[]}
config.module_blacklist = None
config.statement_whitelist={'if','for','return', 'pass', 'subscript'}
config.function_blacklist = {'open', 'eval', 'exec', 'compile', '__import__'}
 

def walk_groups(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = analyzer2.critical_node_names
    crit = analyzer2.critical_nodes
    grps = analyzer2.concurrency_groups
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = ast.unparse(c).strip()
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
            code = ast.unparse(c).strip()
            print(gn + " = " + code)
        except Exception:
            pass
    for n in analyzer2.node_lookup.keys():
        nodec = analyzer2.node_lookup[n]
        if not nodec.dependency_visited:
            continue
        try:
            code = ast.unparse(n).strip()
            result2 = " ".join([named[item] for item in nodec.dependency])
            print(nodec.assigned_concurrency_group.name + ": " + result2 + " " + code)
        except Exception:
            pass
    pass


class TestSplitterAnalyzerModule(unittest.TestCase):
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
    def test_ambiguous_split(self):
        source_code = """
a=[search_email(9,0), 2]
return search_email(a[1])
"""

        expected = """
a=[search_email(9,0), 2]
return search_email(a[1])


C0 => G0 used by (C1) = search_email(9, 0)
C1 => G1 used by (C2) = search_email(a[1])
C2 => G2 used by () = return search_email(a[1])

G0 <= (C0) : uses 
G1 <= (C1) : uses G0
G2 <= (C2) : uses G1

G0 = search_email(9, 0)
G1 = search_email(a[1])
G2 = return search_email(a[1])
G1: C1 a = [search_email(9, 0), 2]
G1: C1 [search_email(9, 0), 2]
G0: C1 search_email(9, 0)
G0: C0 search_email
G0: C0 9
G0: C0 0
G1: C1 2
G2:  return search_email(a[1])
G1: C2 search_email(a[1])
G1: C1 search_email
G1: C1 a[1]
G1: C1 a
G1: C1 1"""

        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################
    def test_split(self):
        source_code = """
q=3
a=search_email(q)
sum=a+a2
sum+=q
sum2=sum+3
b=search_email(sum)>>1  or search_teams(sum2)>>2
c=b
return c
"""

        expected = """
q=3
a=search_email(q)
sum=a+a2
sum+=q
sum2=sum+3
b=search_email(sum)>>1  or search_teams(sum2)>>2
c=b
return c


C0 => G0 used by (C1 C2) = search_email(q)
C1 => G1 used by (C3) = search_email(sum)
C2 => G1 used by (C3) = search_teams(sum2)
C3 => G2 used by () = return c

G0 <= (C0) : uses 
G1 <= (C1 C2) : uses G0
G2 <= (C3) : uses G1

G0 = search_email(q)
G1 = search_email(sum)
G1 = search_teams(sum2)
G2 = return c
G0: C0 C1 C2 q = 3
G0: C0 C1 C2 3
G1: C1 C2 a = search_email(q)
G0: C1 C2 search_email(q)
G0: C0 search_email
G0: C0 q
G1: C1 C2 sum = a + a2
G1: C1 C2 a + a2
G1: C1 C2 a
G1: C1 C2 
G1: C1 C2 a2
G1: C1 C2 sum += q
G1: C1 C2 sum
G1: C1 C2 q
G1: C2 sum2 = sum + 3
G1: C2 sum + 3
G1: C2 sum
G1: C2 3
G2: C3 b = search_email(sum) >> 1 or search_teams(sum2) >> 2
G2: C3 search_email(sum) >> 1 or search_teams(sum2) >> 2
G2: C3 
G2: C3 search_email(sum) >> 1
G1: C3 search_email(sum)
G1: C1 search_email
G1: C1 sum
G2: C3 
G2: C3 1
G2: C3 search_teams(sum2) >> 2
G1: C3 search_teams(sum2)
G1: C2 search_teams
G1: C2 sum2
G2: C3 2
G2: C3 c = b
G2: C3 b
G2:  return c
G2: C3 c"""
        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
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


C0 => G0 used by (C1 C2 C3) = search_teams(0)
C1 => G1 used by (C3) = search_email(1)
C2 => G1 used by (C3) = search_email(2)
C3 => G2 used by (C4) = search_teams(a)
C4 => G3 used by () = return search_teams(a)

G0 <= (C0) : uses 
G1 <= (C1 C2) : uses G0
G2 <= (C3) : uses G0 G1 G_a
G3 <= (C4) : uses G2
G_a <= () : uses G1

G0 = search_teams(0)
G1 = search_email(1)
G1 = search_email(2)
G2 = search_teams(a)
G3 = return search_teams(a)
G1: C1 C2 C3 n = search_teams(0)
G0: C1 C2 C3 search_teams(0)
G0: C0 search_teams
G0: C0 0
G1: C1 C2 C3 n == 3
G1: C1 C2 C3 n
G1: C1 C2 C3 
G1: C1 C2 C3 3
G2: C3 a = search_email(1)
G1: C3 search_email(1)
G1: C1 search_email
G1: C1 1
G2: C3 a = search_email(2)
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
 ##############
                    

if __name__ == "__main__":
    unittest.main()
