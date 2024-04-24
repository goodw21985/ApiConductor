
import orchestrator

orchestrator.log("hi")

from typing import Callable

import math
x=math.pi

import ast


x = ast.parse("\nx = 42\nprint(x)")

ast_str = ast_to_source(x)
print(ast_str)

A = Callable[[int, int], int]

value = 2
match *value,:
    case 2:
        print("ok")
    case 3:
        pass
        
def calculate_factorial(n):
    """Calculate the factorial of a given number."""
    A = yield 5
    if n == 0:
        return 1
    else:
        return n * calculate_factorial(n - 1)

def main():
    print("Factorial Calculator")
        
    try:
        number = int(input("Enter a non-negative integer: "))
        if number < 0:
            raise ValueError("Please enter a non-negative integer.")
        factorial = calculate_factorial(number)
        print(f"The f5actorial of {number} is {factorial}.")
    except ValueError as e:
        print(f"Invalid input: {e}")

if __name__ == "__main__":
    main()
