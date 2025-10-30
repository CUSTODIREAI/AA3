"""Factorial implementation with input validation and tests.

Provides an iterative implementation that mirrors the behavior of math.factorial
for error semantics (ValueError for negatives, TypeError for non-integers), with
one additional guard: booleans are rejected as non-integers to avoid surprising
semantics since bool is a subclass of int.

Doctest examples:

>>> factorial(0)
1
>>> factorial(1)
1
>>> factorial(5)
120
>>> factorial(-1)
Traceback (most recent call last):
...
ValueError: n must be >= 0
>>> factorial(5.0)
Traceback (most recent call last):
...
TypeError: n must be an int
>>> factorial(True)
Traceback (most recent call last):
...
TypeError: n must be an int (not bool)
"""

from __future__ import annotations

from typing import Any
import doctest
import sys
import unittest

__all__ = ["factorial"]


def factorial(n: int) -> int:
    """Compute n! iteratively with strict validation.

    - Rejects booleans as invalid input.
    - Raises ValueError for negative integers.
    - Raises TypeError for non-integer inputs.

    Parameters
    ----------
    n : int
        Non-negative integer for which to compute factorial.

    Returns
    -------
    int
        The factorial of n.
    """
    # Explicitly reject booleans (bool is a subclass of int in Python)
    if isinstance(n, bool):
        raise TypeError("n must be an int (not bool)")

    if not isinstance(n, int):
        raise TypeError("n must be an int")

    if n < 0:
        raise ValueError("n must be >= 0")

    result = 1
    # Early return for 0 or 1
    if n <= 1:
        return result

    for i in range(2, n + 1):
        result *= i
    return result


class TestFactorial(unittest.TestCase):
    def test_zero_and_one(self) -> None:
        self.assertEqual(factorial(0), 1)
        self.assertEqual(factorial(1), 1)

    def test_small_values(self) -> None:
        self.assertEqual(factorial(2), 2)
        self.assertEqual(factorial(3), 6)
        self.assertEqual(factorial(5), 120)
        self.assertEqual(factorial(6), 720)

    def test_larger_value(self) -> None:
        # Known value for 20!
        self.assertEqual(factorial(20), 2432902008176640000)

    def test_negative_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            factorial(-1)

    def test_type_errors(self) -> None:
        for bad in (5.0, "5", None, 3.14, [5], {"n": 5}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    factorial(bad)  # type: ignore[arg-type]

    def test_bool_rejected(self) -> None:
        with self.assertRaises(TypeError):
            factorial(True)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            factorial(False)  # type: ignore[arg-type]


if __name__ == "__main__":
    # Run doctests first, then unittests. Exit non-zero if any fail.
    failures, _ = doctest.testmod(optionflags=doctest.ELLIPSIS)

    # Build and run tests explicitly to combine results with doctest outcome
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestFactorial)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    exit_code = 0 if failures == 0 and result.wasSuccessful() else 1
    sys.exit(exit_code)
