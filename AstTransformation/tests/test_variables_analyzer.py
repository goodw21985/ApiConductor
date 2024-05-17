from symtable import SymbolTable
import unittest

import ast
from ast_transform import astor_fork
from ast_transform import scope_analyzer
from ast_transform import common
from ast_transform import variables_analyzer
from unittest.mock import patch
import io



def Nodes(list):
    last = list[-1]

    return "#" + str(last.lineno)

rename = {
    "read": "r",
    "write": "w",
    "readwrite": "rw",
    "declared": ":",
    "ambiguous": "m",
}

def print_critical(analyzer):
    for critical in analyzer.critical_nodes:
        name = analyzer.critical_node_names[critical]
        if critical in analyzer.non_concurrent_critical_nodes:
            name += " non-concurrent "
        elif critical in analyzer.critical_nodes_if_groups:
            name += " => "+analyzer.critical_nodes_if_groups[critical]
        else:
            name += " concurrent "
        print(name)
    
def walk(t, pre=""):
    for name in t.keys():
        v = t[name]
        suffix=""
        if v.is_set_unambiguously_across_if_blocks():
            suffix += " is_set_unambiguously_across_if_blocks"
        if isinstance(name, str):
            print(f"{pre}{name}{suffix}")
        elif isinstance(name, ast.ClassDef):
            print(f"{pre}{name.name}{suffix}")
        elif isinstance(name, ast.FunctionDef):
            print(f"{pre}{name.name}{suffix}")
        else:
            tname=type(name).__name__
            print(f"{pre}{tname}{suffix}")
        if v.child:
            walk(v.child, pre + ". ")
        if v.redirect:
            print(f"{pre}| redirect")
        if v.notLocal == True:
            print(f"{pre}| notlocal")

        for tuple1 in v.usage:
            x = tuple1[0]
            y = tuple1[1]
            print(f"{pre}| {rename[x]} {Nodes(y.ancestors)}")
            


config = common.Config()
config.awaitable_functions = ["search_email", "search_teams"]
config.module_blacklist = None


class TestVariablesAnalyzerModule(unittest.TestCase):
    @patch("sys.stdout", new_callable=io.StringIO)
    def check(self,source_code,expected, mock_stdout):
        # Test your function here
        tree = ast.parse(source_code)

        analyzer1 = variables_analyzer.Scan(tree, config)
        print_critical(analyzer1)
        walk(analyzer1.symbol_table)
        result = mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

    def runit(self,source_code):
        tree = ast.parse(source_code)

        analyzer1 = variables_analyzer.Scan(tree, config)
        walk(analyzer1.symbol_table)

##############
    def test_ifreuse(self):
        source_code = """
a=None
if n:
    a=search_email()
elif j:
    if t:
        a=search_teams()
    else:
        a=None
"""

        expected = """
C0 => a
C1 => a
a is_set_unambiguously_across_if_blocks
| w #2
| w #4
| w #7
| w #9
n
| r #3
search_email
| r #4
j
| r #5
t
| r #6
search_teams
| r #7"""
        self.check(source_code,expected)        
##############
    def test_ifreuse2(self):
        source_code = """
a=None
if n:
    for i in range(2):
        a=search_email()
elif j:
    if t:
        a=search_teams()
"""

        expected = """
C0 non-concurrent 
C1 non-concurrent 
a
| w #2
| w #5
| w #8
n
| r #3
i
| m #4
range
| r #4
search_email
| r #5
j
| r #6
t
| r #7
search_teams
| r #8"""
        self.check(source_code,expected)        
##############
    def test_ifreuse3(self):
        source_code = """
a=None
if n:
    a=search_email()
elif j:
    if t:
        a=search_teams()
if q:
    a=search_teams()

"""

        expected = """
C0 non-concurrent 
C1 non-concurrent 
C2 non-concurrent 
a
| w #2
| w #4
| w #7
| w #9
n
| r #3
search_email
| r #4
j
| r #5
t
| r #6
search_teams
| r #7
| r #9
q
| r #8"""
        self.check(source_code,expected)        
##############
    def test_simple(self):
        source_code = """
a=[search_email(9,0), 2]
b=a[1]
return search_email(b)
"""

        expected = """
C0 concurrent 
C1 concurrent 
a
| w #2
| r #3
search_email
| r #2
| r #4
b
| w #3
| r #4"""
        self.check(source_code,expected)        

#######################
    def test_complex(self):
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

        expected = """
m
| rw #2
| r #29
a
| m #3
| m #3
| r #3
| r #3
| r #29
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
. . Lambda
. . . x
. . . | r #13
. . . | : #13
. . . | r #13
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
y
| notlocal
| w #10
| r #13
kjj
obj
| w #26
| r #27
| r #27
MyClass
| r #26
func
| w #27
| r #28
print
| r #28"""
        self.check(source_code,expected)        
##############

if __name__ == "__main__":
    unittest.main()
