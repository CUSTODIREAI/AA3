import os
import sys
import doctest
import unittest

# Ensure 'src' is on sys.path for src/ layout
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_DIR = os.path.join(ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from factorial_pkg.factorial import factorial
import factorial_pkg.factorial as factorial_module


class TestFactorial(unittest.TestCase):
    def test_values(self):
        self.assertEqual(factorial(0), 1)
        self.assertEqual(factorial(1), 1)
        self.assertEqual(factorial(2), 2)
        self.assertEqual(factorial(5), 120)
        self.assertEqual(factorial(10), 3628800)
        self.assertEqual(factorial(20), 2432902008176640000)

    def test_type_error(self):
        with self.assertRaises(TypeError):
            factorial(3.5)
        with self.assertRaises(TypeError):
            factorial(True)
        with self.assertRaises(TypeError):
            factorial('3')
        with self.assertRaises(TypeError):
            factorial(None)

    def test_value_error(self):
        with self.assertRaises(ValueError):
            factorial(-1)

    def test_doctests(self):
        failures, _ = doctest.testmod(factorial_module, optionflags=doctest.ELLIPSIS)
        self.assertEqual(failures, 0)


if __name__ == '__main__':
    unittest.main()
