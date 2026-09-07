"""test_calc.py — factorial 单元测试"""

from calc import factorial


def test_factorial_5():
    assert factorial(5) == 120
