import unittest

from ast_transform import mock_framework
import ast


class TestMockModule(unittest.TestCase):
    def check(self, lib, src):
        m=mock_framework.Mock(lib,src)
        self.assertEqual(m.capture2, m.capture1)

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