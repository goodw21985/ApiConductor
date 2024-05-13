import unittest

from ast_transform import mock_framework
import ast


class TestMockModuleQuick(unittest.TestCase):
    def check(self, lib, src, inputs=None):
        m=mock_framework.Mock(lib,src, inputs)
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

if __name__ == "__main__":
    unittest.main()
