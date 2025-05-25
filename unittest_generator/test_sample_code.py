import pytest
from sample_code import add_numbers, multiply_numbers, divide_numbers, Calculator, factorial

def test_add_numbers():
    # Test normal addition
    assert add_numbers(5, 3) == 8
    assert add_numbers(-2, 3) == 1
    assert add_numbers(5.5, 3.5) == 9.0
    
    # Test invalid input
    with pytest.raises(TypeError):
        add_numbers("5", 3)
    with pytest.raises(TypeError):
        add_numbers(5, "3")

def test_multiply_numbers():
    # Test normal multiplication
    assert multiply_numbers(5, 3) == 15
    assert multiply_numbers(-2, 3) == -6
    assert multiply_numbers(5.5, 3.5) == 19.25
    
    # Test invalid input
    with pytest.raises(TypeError):
        multiply_numbers("5", 3)
    with pytest.raises(TypeError):
        multiply_numbers(5, "3")

def test_divide_numbers():
    # Test normal division
    assert divide_numbers(10, 2) == 5
    assert divide_numbers(10, -2) == -5
    assert divide_numbers(10.5, 2) == 5.25
    
    # Test division by zero
    with pytest.raises(ValueError):
        divide_numbers(5, 0)
    
    # Test invalid input
    with pytest.raises(TypeError):
        divide_numbers("5", 3)
    with pytest.raises(TypeError):
        divide_numbers(5, "3")

def test_factorial():
    # Test normal factorial calculation
    assert factorial(5) == 120
    assert factorial(0) == 1
    assert factorial(1) == 1
    
    # Test invalid input
    with pytest.raises(ValueError):
        factorial(-1)
    with pytest.raises(TypeError):
        factorial("5")

def test_calculator_init():
    calc = Calculator()
    assert calc.get_history() == []

def test_calculator_add():
    calc = Calculator()
    # Test normal addition
    assert calc.add(5, 3) == 8
    assert calc.add(-2, 3) == 1
    assert calc.add(5.5, 3.5) == 9.0
    
    # Verify history
    history = calc.get_history()
    assert len(history) == 3
    assert history[0] == "5 + 3 = 8"
    
    # Test invalid input
    with pytest.raises(TypeError):
        calc.add("5", 3)

def test_calculator_multiply():
    calc = Calculator()
    # Test normal multiplication
    assert calc.multiply(5, 3) == 15
    assert calc.multiply(-2, 3) == -6
    assert calc.multiply(5.5, 3.5) == 19.25
    
    # Verify history
    history = calc.get_history()
    assert len(history) == 3
    assert history[0] == "5 * 3 = 15"
    
    # Test invalid input
    with pytest.raises(TypeError):
        calc.multiply("5", 3)

def test_calculator_divide():
    calc = Calculator()
    # Test normal division
    assert calc.divide(10, 2) == 5
    assert calc.divide(10, -2) == -5
    assert calc.divide(10.5, 2) == 5.25
    
    # Verify history
    history = calc.get_history()
    assert len(history) == 3
    assert history[0] == "10 / 2 = 5"
    
    # Test division by zero
    with pytest.raises(ValueError):
        calc.divide(5, 0)
    
    # Test invalid input
    with pytest.raises(TypeError):
        calc.divide("5", 3)

def test_calculator_get_history():
    calc = Calculator()
    calc.add(5, 3)
    calc.multiply(5, 3)
    
    history = calc.get_history()
    assert len(history) == 2
    assert history[0] == "5 + 3 = 8"
    assert history[1] == "5 * 3 = 15"
    
    # Modify the copied history and verify original remains unchanged
    history[0] = "Modified"
    assert calc.get_history()[0] == "5 + 3 = 8"

def test_calculator_clear_history():
    calc = Calculator()
    calc.add(5, 3)
    calc.multiply(5, 3)
    
    assert len(calc.get_history()) == 2
    
    calc.clear_history()
    assert len(calc.get_history()) == 0