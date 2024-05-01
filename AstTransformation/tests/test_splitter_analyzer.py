import unittest

import ast
from ast_transform import astor

from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from unittest.mock import patch
import io

config = scope_analyzer.Config()
config.awaitableFunctions= ["search_email", "search_teams","search_meetings"]
config.moduleBlackList=None
config.useAsync=False


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

expected="""
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
G1: C1 C2 search_email(q)
G0: C0 search_email
G0: C0 q
G0: C0 C1 C2 q = 3
G0: C0 C1 C2 3
G2: C3 search_email(sum)
G1: C1 search_email
G1: C1 sum
G1: C1 C2 sum = a + a2
G1: C1 C2 a + a2
G1: C1 C2 a
G1: C1 C2 a = search_email(q)
G1: C1 C2 a2
G1: C1 C2 sum += q
G1: C1 C2 sum
G1: C1 C2 q
G2: C3 search_teams(sum2)
G1: C2 search_teams
G1: C2 sum2
G1: C2 sum2 = sum + 3
G1: C2 sum + 3
G1: C2 sum
G1: C2 3
G2:  return c
G2: C3 c
G2: C3 c = b
G2: C3 b
G2: C3 b = search_email(sum) >> 1 or search_teams(sum2) >> 2
G2: C3 search_email(sum) >> 1 or search_teams(sum2) >> 2
G2: C3 search_email(sum) >> 1
G2: C3 1
G2: C3 search_teams(sum2) >> 2
G2: C3 2"""

def walk_groups(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = {}
    crit = analyzer2.critical_nodes
    grps=analyzer2.concurrency_groups
    num = 0
    for c in crit:
        named[c]= "C"+str(num)
        num+=1
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = astor.to_source(c).strip()
            nodec = analyzer2.nodelookup[c]
            result = ' '.join([named[item] for item in nodec.dependency])

            print(named[c] + " => " + gn + " used by ("+result+")"+" = "+ code)
        except Exception:
            pass

    print()

    for n in grps:
        result = ' '.join([item.name for item in n.group_dependencies])
        resultn = ' '.join([named[item] for item in n.grouped_critical_nodes])
        print(n.name+" <= (" + resultn+ ") : uses "+result)
        
    print()

def walk_nodes(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = {}
    crit = analyzer2.critical_nodes
    num = 0
    for c in crit:
        named[c]= "C"+str(num)
        num+=1
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = astor.to_source(c).strip()
            print(gn + " = "+code)
        except Exception:
            pass
    for n in analyzer2.nodelookup.keys():
        nodec = analyzer2.nodelookup[n]
        if not nodec.dependecyVisited:
            continue
        try:
            code = astor.to_source(n).strip()
            result2 = ' '.join([named[item] for item in nodec.dependency])
            print(nodec.concurrency_group.name+": "+result2+" "+code)
        except Exception:
            pass
    pass


class TestSplitterAnalyzerModule(unittest.TestCase):
    def test_split(self):
        result=self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
        
    def get(self, code):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print(code)
            print()

            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, config)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
            walk_groups(analyzer3)
            walk_nodes(analyzer3)
            result=mock_stdout.getvalue().strip()
            return result
        
if __name__ == '__main__':
    unittest.main()