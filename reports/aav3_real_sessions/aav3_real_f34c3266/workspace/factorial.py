from typing import Union, SupportsIndex
import operator

__all__ = ["factorial"]

def factorial(n: Union[int, SupportsIndex]) -> int:
    """Compute n! (factorial) with strict input validation.

    Accepts integer-like inputs via __index__ and rejects non-integers and bools.

    Rules:
    - bool is not allowed (reject True/False to avoid confusion with 1/0)
    - Non-integer-like values raise TypeError
    - Negative integers raise ValueError

    Examples
    --------
    >>> factorial(0)
    1
    >>> factorial(5)
    120
    >>> factorial(-1)
    Traceback (most recent call last):
    ...
    ValueError: n must be a non-negative integer
    >>> factorial(5.0)
    Traceback (most recent call last):
    ...
    TypeError: n must be an integer
    >>> factorial(True)
    Traceback (most recent call last):
    ...
    TypeError: bool is not allowed
    """

    if isinstance(n, bool):
        # Explicitly disallow bool to avoid treating True/False as 1/0.
        raise TypeError("bool is not allowed")

    try:
        k = operator.index(n)  # supports int-like types implementing __index__
    except TypeError:
        raise TypeError("n must be an integer") from None

    if k < 0:
        raise ValueError("n must be a non-negative integer")

    result = 1
    # Iterative approach avoids recursion depth issues for large n
    for i in range(2, k + 1):
        result *= i
    return result


if __name__ == "__main__":
    import doctest
    doctest.testmod()
