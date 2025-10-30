'''Reliable factorial implementation with strict validation.

- Accepts integer-like types via the __index__ protocol (e.g., numpy.int64).
- Explicitly rejects bool (even though it's a subclass of int) for clarity.
- Raises ValueError for negative values.
- Iterative computation avoids recursion limits and stack overhead.

Examples
--------
>>> factorial(0)
1
>>> factorial(5)
120
>>> factorial(True)  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
TypeError: ...
>>> factorial(-3)  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
ValueError: ...
>>> factorial(5.0)  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
TypeError: ...
'''
from __future__ import annotations

import operator as _op
from typing import SupportsIndex

__all__ = ["factorial"]


def factorial(n: SupportsIndex) -> int:
    """Compute n! for a non-negative, integer-like input.

    - Accepts integer-like types via ``__index__``.
    - Rejects ``bool`` inputs explicitly with ``TypeError``.
    - Raises ``ValueError`` for negative integers.

    Parameters
    ----------
    n : SupportsIndex
        Non-negative integer-like value.

    Returns
    -------
    int
        The factorial of ``n``.
    """
    if isinstance(n, bool):
        # Explicitly reject bool for clarity and to avoid surprising behavior.
        raise TypeError("factorial() does not accept bool")

    try:
        k = _op.index(n)  # Coerce integer-like inputs (e.g., numpy ints)
    except Exception as exc:  # noqa: BLE001 - bubble as TypeError for clarity
        raise TypeError("factorial() only accepts integer-like values") from exc

    if k < 0:
        raise ValueError("factorial() not defined for negative values")

    result = 1
    # Fast path for small k
    if k < 2:
        return 1

    # Iterative multiplication to avoid recursion limits and overhead
    for i in range(2, k + 1):
        result *= i
    return result


if __name__ == "__main__":
    import doctest
    import math

    # Run doctests embedded in the module docstring
    doctest.testmod()

    # Sanity checks against math.factorial for a quick range
    for i in range(0, 21):
        assert factorial(i) == math.factorial(i)

    print("factorial.py: self-checks passed.")
