import unittest

import ast
from ast_transform import astor

from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from unittest.mock import patch
import io

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code = """
q=3
a=search_email(q)
sum=a+a2
sum+=q
sum2=sum+3
b=search_email(sum)  or search_teams(sum2)
c=b
return c
"""

expected="""
"""

def walk_groups(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = {}
    crit = analyzer2.critical_nodes
    grps=analyzer2.critical_dependency_groups
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
        try:
            code = astor.to_source(n).strip()
            result = ' '.join([item.name for item in nodec.concurrency_groups])
            result2 = ' '.join([named[item] for item in nodec.dependency])
            print(result+":"+result2+" "+code)
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
            analyzer1 = variables_analyzer.Scan(tree, awaitable_functions)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
            walk_groups(analyzer3)
            walk_nodes(analyzer3)
            result=mock_stdout.getvalue().strip()
            return result
        
if __name__ == '__main__':
    unittest.main()