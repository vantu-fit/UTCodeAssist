def add_numbers(a, b):
    """Add two numbers and return the result."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be numbers")
    return a + b

def multiply_numbers(a, b):
    """Multiply two numbers and return the result."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be numbers")
    return a * b

def divide_numbers(a, b):
    """Divide two numbers and return the result."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be numbers")
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = add_numbers(a, b)
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a, b):
        result = multiply_numbers(a, b)
        self.history.append(f"{a} * {b} = {result}")
        return result
    
    def divide(self, a, b):
        result = divide_numbers(a, b)
        self.history.append(f"{a} / {b} = {result}")
        return result
    
    def get_history(self):
        return self.history.copy()
    
    def clear_history(self):
        self.history.clear()

def factorial(n):
    """Calculate factorial of a number."""
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)

if __name__ == "__main__":
    # Example usage
    calc = Calculator()
    print(calc.add(5, 3))
    print(calc.multiply(4, 7))
    print(calc.divide(10, 2))
    print(f"History: {calc.get_history()}")
    print(f"Factorial of 5: {factorial(5)}")