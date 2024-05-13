import unittest

from ast_transform import mock_framework
import ast


class TestMockModuleQuick(unittest.TestCase):
    def check(self, lib, src):
        m=mock_framework.Mock(lib,src)
        self.assertEqual(m.capture2, m.capture1)

#######################
    def test_simple_if(self):
        lib = """
def search_email(a=0):
    return a
"""

        src = """
x=3
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""
        self.check(lib, src)

#######################

if __name__ == "__main__":
    unittest.main()
