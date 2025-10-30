'''Factorial computation.

Provides a strict, iterative factorial implementation with doctests.
'''

def factorial(n: int) -> int:
    '''
    Compute n! for a non-negative integer n.

    Parameters
    ----------
    n : int
        Non-negative integer.

    Returns
    -------
    int

    Examples
    --------
    >>> from factorial_pkg.factorial import factorial
    >>> factorial(0)
    1
    >>> factorial(5)
    120
    >>> factorial(10)
    3628800
    >>> factorial(3.0)  # floats not allowed even if integer-like
    Traceback (most recent call last):
    ...
    TypeError: n must be an int, got float
    >>> factorial(True)
    Traceback (most recent call last):
    ...
    TypeError: n must be an int, got bool
    >>> factorial(-1)
    Traceback (most recent call last):
    ...
    ValueError: n must be >= 0
    '''
    if type(n) is not int:
        raise TypeError(f'n must be an int, got {type(n).__name__}')
    if n < 0:
        raise ValueError('n must be >= 0')
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
