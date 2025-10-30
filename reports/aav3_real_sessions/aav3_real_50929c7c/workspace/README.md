# Custodire Factorial

A small, importable factorial implementation with explicit input validation, doctest examples, and a pytest-based unit test suite.

Input rules:
- Accepts integers and int-like objects implementing __index__.
- Rejects bool explicitly to avoid surprises.
- Rejects non-integral numerics like float, Decimal, Fraction.
- Raises ValueError for negative values.

Why iterative:
- Avoids recursion depth issues.
- Clear and sufficiently fast for typical inputs.
- Keeps behavior explicit; can swap to math.factorial later if needed.

Quick checks:
- Doctests: `python -m doctest -v src/custodire_factorial/factorial.py`
- Unit tests: `pip install -e . && pytest -q`

Notes:
- Targets Python 3.10+.
- Very large n will be slow due to big integer arithmetic.
