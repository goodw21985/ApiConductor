import unittest

import ast
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
| rw #2
| r #29
a
| m #3
| r #3
| r #3
| r #3
| r #29
MyClass
. __init__
. x
. | w #12
. my_function
. . m
. . | redirect
. . y
. . | redirect
. . kjj
. . | redirect
. . y1
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
. . . | rw #21
. . . mf2
. . . . y2
. . . . | redirect
. . . . y1
. . . . | rw #20
. . y2
. other
| r #26
y
| w #10
| r #13
kjj
obj
| w #26
| r #27
| r #27
func
| w #27
| r #28
print
| r #28"""

def Nodes(list):
    last = list[-1]
    
    return "#"+str(last.lineno)
    

def walk(t, pre=""):
    for name in t.keys():
        v = t[name]
        print(f"{pre}{name}")
        for x in v.keys():
            if (x=="children"):
                walk(v[x], pre+". ");
            elif (x=="redirect"):
                print(f"{pre}| {x}")
            else:
                for y in v[x]:
                    print(f"{pre}| {x} {Nodes(y)}")


class TestVariablesAnalyzerModule(unittest.TestCase):
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_walk(self, mock_stdout):
        # Test your function here
        tree = ast.parse(source_code)
        analyzer1= variables_analyzer.Scan(tree, [])
        walk(analyzer1.symbol_table)
        result=mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

if __name__ == '__main__':
    unittest.main()