import math
import pytest

from custodire_factorial import factorial


class IntLike:
    def __init__(self, value):
        self.value = value
    def __index__(self):
        return int(self.value)


def test_small_values():
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    assert factorial(10) == 3628800


def test_matches_math_factorial_up_to_50():
    for n in range(0, 50):
        assert factorial(n) == math.factorial(n)


def test_rejects_bool():
    with pytest.raises(TypeError):
        factorial(True)
    with pytest.raises(TypeError):
        factorial(False)


def test_rejects_float():
    with pytest.raises(TypeError) as excinfo:
        factorial(5.0)
    assert 'integer' in str(excinfo.value)


def test_negative_raises():
    with pytest.raises(ValueError):
        factorial(-1)


def test_accepts_index_protocol():
    seven = IntLike(7)
    assert factorial(seven) == math.factorial(7)
