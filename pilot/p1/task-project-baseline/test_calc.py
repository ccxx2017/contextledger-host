"""test_calc.py — factorial 基本验证"""

import unittest

from calc import factorial


class TestFactorial(unittest.TestCase):
    def test_factorial_5(self):
        self.assertEqual(factorial(5), 120)


if __name__ == "__main__":
    unittest.main()
