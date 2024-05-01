from symtable import SymbolTable
import unittest

import ast
from ast_transform import astor
from ast_transform import scope_analyzer
from ast_transform import variables_analyzer
from unittest.mock import patch
import io

source_code = """
m+=3
a.b+=a.m
class MyClass:
    def __init__(self):
        self.x=3

    def my_function(self):
        global m, y, kjj
        y=3
        y1=4
        self.x=4
        return lambda x: x ** y
        
        def mf2():
            nonlocal y1, y2
            y1+=3
            def mf2():
                nonlocal y2
                y1+=3
                y2+=3

    @staticmethod
    def other():
        return False
obj = MyClass()
func = obj.my_function()
print(func(3))
return a,m
"""

expected="""
m
| r #29
| rw #2
a
| r #3
| r #3
| r #3
| r #29
| m #3
MyClass
. __init__
. x
. | w #6
. | w #12
. my_function
. . m
. . | redirect
. . y
. . | redirect
. . kjj
. . | redirect
. . y1
. . | notlocal
. . | w #11
. . | rw #17
. . lambda
. . . x
. . . | r #13
. . . | r #13
. . . | : #13
. . mf2
. . . y1
. . . | redirect
. . . y2
. . . | redirect
. . . mf2
. . . . y2
. . . . | redirect
. . . . y1
. . . . | rw #20
. . y2
. . | notlocal
. . | rw #21
. other
| r #26
y
| notlocal
| r #13
| w #10
kjj
obj
| r #27
| r #27
| w #26
func
| r #28
| w #27
print
| r #28"""

def Nodes(list):
    last = list[-1]
    
    return "#"+str(last.lineno)
    
attr = [scope_analyzer.SymbolTableEntry.attr_read, scope_analyzer.SymbolTableEntry.attr_write, scope_analyzer.SymbolTableEntry.attr_read_write, scope_analyzer.SymbolTableEntry.attr_declared, scope_analyzer.SymbolTableEntry.attr_ambiguous]

rename = {"read":"r", "write":"w", "readwrite":"rw", "declared":":", "ambiguous":"m"}
def walk(t, pre=""):
    for name in t.keys():
        v = t[name]
        print(f"{pre}{name}")
        if v.child:
            walk(v.child, pre+". ");
        if v.redirect:
            print(f"{pre}| redirect")
        if v.notLocal == True:
            print(f"{pre}| notlocal")
        for x in attr:
            if v[x]:
                for y in v[x]:
                    print(f"{pre}| {rename[x]} {Nodes(y)}")

config = scope_analyzer.Config()
config.awaitableFunctions= []
config.moduleBlackList=None
config.useAsync=False


class TestVariablesAnalyzerModule(unittest.TestCase):
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_walk(self, mock_stdout):
        # Test your function here
        tree = ast.parse(source_code)

        analyzer1= variables_analyzer.Scan(tree, config)
        walk(analyzer1.symbol_table)
        result=mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()