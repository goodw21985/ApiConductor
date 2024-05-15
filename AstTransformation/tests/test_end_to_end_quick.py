import unittest

from ast_transform import mock_framework
import ast


class TestMockModuleQuick(unittest.TestCase):
    def check(self, lib, src, inputs=None):
        m=mock_framework.Mock(lib,src, inputs)
        self.assertEqual(m.capture2, m.capture1)

#######################
    def test_set_comprehension(self):
        lib = """
def compute_value(item):
    # Simulate some computation that might be optimized through parallel processing
    import time
    time.sleep(0.1)  # Delay to mimic a time-consuming computation
    return item + 100
"""

        src = """
processed_values = {compute_value(item) for item in range(10) if item % 2 == 0}
return ",".join(str(item) for item in list(processed_values))
"""

        inputs = """
"""
        self.check(lib, src, inputs)

#######
if __name__ == "__main__":
    unittest.main()
