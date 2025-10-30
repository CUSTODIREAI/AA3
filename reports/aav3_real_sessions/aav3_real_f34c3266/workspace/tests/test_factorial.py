import math
import unittest

from factorial import factorial


class IndexableInt:
    def __init__(self, value: int) -> None:
        self._value = int(value)

    def __index__(self) -> int:
        return self._value


class TestFactorial(unittest.TestCase):
    def test_zero_and_one(self):
        self.assertEqual(factorial(0), 1)
        self.assertEqual(factorial(1), 1)

    def test_small_values(self):
        for n in range(2, 12):
            with self.subTest(n=n):
                self.assertEqual(factorial(n), math.factorial(n))

    def test_large_value(self):
        n = 200
        self.assertEqual(factorial(n), math.factorial(n))
        self.assertIsInstance(factorial(n), int)

    def test_supports_index(self):
        n = IndexableInt(5)
        self.assertEqual(factorial(n), 120)

    def test_negative_raises_value_error(self):
        with self.assertRaises(ValueError):
            factorial(-1)
        with self.assertRaises(ValueError):
            factorial(IndexableInt(-3))

    def test_non_integer_raises_type_error(self):
        with self.assertRaises(TypeError):
            factorial(5.0)
        with self.assertRaises(TypeError):
            factorial("6")  # type: ignore[arg-type]

    def test_bool_rejected(self):
        with self.assertRaises(TypeError):
            factorial(True)
        with self.assertRaises(TypeError):
            factorial(False)

    def test_type_of_result(self):
        self.assertIs(type(factorial(10)), int)


if __name__ == "__main__":
    unittest.main()
