from re import X
from ast_transform import Util
from ast_transform import astor
from ast_transform import transform
from ast_transform import variables_analyzer
import ast
import io


# Example usage:
# Example usage
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

"""

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

tree = ast.parse(source_code)
t= variables_analyzer.Scan(tree)
walk(t)

with open('examples/client_library.py', 'r') as file:
    client_code = file.read()

client_library_tree = ast.parse(client_code)

with open('examples/safety.py', 'r') as file:
    safety_code = file.read()
    
safety_tree = ast.parse(safety_code)

statement_to_add = "print('Added statement')"

modified_code = transform.modify_code(original_code, statement_to_add)
print(modified_code)


module2.Run()
