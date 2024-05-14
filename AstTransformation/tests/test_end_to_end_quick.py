import unittest

from ast_transform import mock_framework
import ast


class TestMockModuleQuick(unittest.TestCase):
    def check(self, lib, src, inputs=None):
        m=mock_framework.Mock(lib,src, inputs)
        self.assertEqual(m.capture2, m.capture1)

#######################
    def test_dict_and_string_manipulation(self):
        lib = """
def create_dict(a=0, b=1):
    return {'num': a, 'double': a*2, 'sum': a+b}

def wrap_string(s=''):
    return f'--{s}--'
"""

        src = """
inputs = {'a': 10, 'b': 20}  # These values could be varied in the 'inputs' string
result_dict = create_dict(inputs['a'], inputs['b'])

# Use a lambda function to process the dictionary and create a string
process_dict = lambda d: ','.join(f'{k}={v}' for k, v in d.items())
processed_string = process_dict(result_dict)

# Final result after wrapping the processed string
return wrap_string(processed_string)
"""

        inputs = """
{'a': [10, 15, 20], 'b': [20, 25, 30]}
"""     
        self.check(lib, src, inputs)

#######
if __name__ == "__main__":
    unittest.main()
