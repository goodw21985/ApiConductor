import unittest

from ast_transform import mock_framework
import ast


class TestMockModuleQuick(unittest.TestCase):
    def check(self, lib, src, inputs=None):
        m=mock_framework.Mock(lib,src, inputs)
        self.assertEqual(m.capture2, m.capture1)

#######################
    def test_incomplete_if(self):
        lib = """
def search_email(a=0):
    return a
"""

        src = """
val=0
for a in range(3):
    val+=search_email(a)
return val;
"""

        inputs = """
"""
        self.check(lib, src, inputs)
#######################

if __name__ == "__main__":
    unittest.main()
