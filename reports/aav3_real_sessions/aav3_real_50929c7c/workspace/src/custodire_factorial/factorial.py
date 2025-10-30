'''Iterative factorial with strict input validation.

This function computes n! for non-negative integers using a simple loop,
with explicit checks to mirror common expectations:
- Accepts integers and int-like objects (via __index__).
- Rejects bool explicitly to avoid surprising behavior.
- Rejects non-integral numerics (e.g., float, Decimal, Fraction) with TypeError.
- Raises ValueError for negative inputs.

Examples
--------
>>> factorial(0)
1
>>> factorial(5)
120
>>> factorial(1)
1
>>> factorial(10)
3628800
>>> factorial(5.0)  # doctest: +ELLIPSIS
Traceback (most recent call last):
...
TypeError: factorial() argument must be an integer, not float
>>> factorial(-1)  # doctest: +ELLIPSIS
Traceback (most recent call last):
...
ValueError: factorial() not defined for negative values
>>> factorial(True)  # doctest: +ELLIPSIS
Traceback (most recent call last):
...
TypeError: factorial() does not accept bool
>>> class IntLike:
...     def __index__(self): return 7
>>> factorial(IntLike())
5040
'''

from operator import index as _index
from typing import SupportsIndex

__all__ = ['factorial']

def factorial(n: SupportsIndex) -> int:
    '''Compute n! for a non-negative integer with strict validation.

    Parameters
    ----------
    n: SupportsIndex
        A non-negative integer or int-like object implementing __index__.

    Returns
    -------
    int
        The factorial of n.

    Raises
    ------
    TypeError
        If n is not an integer-like value or is a bool.
    ValueError
        If n is negative.
    '''
    if isinstance(n, bool):
        raise TypeError('factorial() does not accept bool')
    try:
        k = _index(n)
    except TypeError:
        raise TypeError(f'factorial() argument must be an integer, not {type(n).__name__}') from None
    if k < 0:
        raise ValueError('factorial() not defined for negative values')
    result = 1
    for i in range(2, k + 1):
        result *= i
    return result

if __name__ == '__main__':
    import doctest
    doctest.testmod()
