import unittest

from ast_transform import mock_framework
import ast


class TestMockModule(unittest.TestCase):
    def check(self, lib, src, variables = ""):
        m=mock_framework.Mock(lib,src, variables)
        self.assertEqual(m.capture2, m.capture1)

#######################
    def test_simple_if(self):
        lib = """
def search_email(a=0):
    return a
"""

        src = """
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""

        inputs = """
x=[2, 3]
"""
        self.check(lib, src, inputs)

#######################
    def test_incomplete_if(self):
        lib = """
def search_email(a=0):
    return a
"""

        src = """
y=None
a=search_email(x)
if (a<3):
    y=search_email(a+5)
elif a>7:
    y=search_email(a+10)
return y
"""

        inputs = """
x=[2, 3, 8]
"""
        self.check(lib, src, inputs)

#######################
    def test_incomplete_if2(self):
        lib = """
def search_email(a=0):
    return a
"""

        src = """
y= None
z=None
a=search_email(x)
if (a<3):
    y=search_email(a+5)
    if (a<1):
        z = search_email(a+10)
    else:
        z = search_email(a)
elif a>7:
    y=search_email(a+10)
return str(y) + "," +str(z)
"""

        inputs = """
x=[0, 2,5, 8]
"""        
    def test_incomplete_if(self):
        lib = """
def search_email(a=0):
    return a
"""
#######################

        src = """
y=None
a=search_email(x)
if (a<3):
    y=search_email(a+5)
elif a>7:
    y=search_email(a+10)
return y
"""

        inputs = """
x=[2,5, 8]
"""
        self.check(lib, src, inputs)
#######################
    def test_dict_follow(self):
        libd = """
def search_email(a='first', b='second'):
    return {a:{'name':"bob", 'age':10}, b:{'name':'jill', 'age':11}}

def search_dog(a='first', b='second'):
    return a['name']+" "+str(a['age']) + "," + b['name']+" "+str(b['age'])
"""

        srcd = """
a=[search_email('a1','a2'), search_email('a3','a4')]
return search_dog(a[0]['a1'], a[1]['a4'])
"""
        self.check(libd, srcd)
#######################
    def test_ambiguous_dependency(self):
        lib = """
def search_email(a=0, b=0):
    return str(a)+ "1"
"""

        src = """
a=[search_email(9,0), 2]
return search_email(a[1])
"""
        self.check(lib, src)
#######################
    def test_missing_return(self):
        lib = """
def search_email(a=0, b=0):
    return str(a)+ "1"
"""

        src = """
b= search_email(1)
"""
        self.check(lib, src)
#######################
    def test_dag_1_to_2(self):
        lib = """
def search_email(a=0, b=0):
    return str(a)+ "1"

def search_meetings(a=0, b=0):
    return str(a)+"2"

def search_teams(a=0, b=0):
    return str(b)+"3"
"""

        src = """
pass
q=3
a=search_email(q,0)
sum=str(a)+'j'
sum += str(q)
sum2=sum + "q"
b=search_meetings(sum+"a") + search_teams(b=sum2+"b")
c=b
return c
"""
        self.check(lib, src)
#######################

if __name__ == "__main__":
    unittest.main()
