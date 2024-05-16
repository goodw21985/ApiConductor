import unittest

from ast_transform import mock_framework
import ast


class TestMockModuleQuick(unittest.TestCase):
    def check(self, lib, src, inputs=None):
        m=mock_framework.Mock(lib,src, inputs)
        self.assertEqual(m.capture2, m.capture1)

#######################
    def test_dict_rev_comprehension(self):
        lib = """
def compute_value(item):
    # Simulate some computation that might be optimized through parallel processing
    return item + 100
"""

        src = """
processed_values = {compute_value(item):item for item in range(10) if item % 2 == 1}
return ",".join(f"{key}:{value}" for key, value in processed_values.items())
"""

        inputs = """
"""
        self.check(lib, src, inputs)

#######
if __name__ == "__main__":
    unittest.main()
