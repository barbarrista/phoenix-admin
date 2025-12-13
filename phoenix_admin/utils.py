from inspect import isclass
from typing import TypeVar

_T = TypeVar("_T")


class NoneValueError(Exception):
    """Raised when None is passed to getval(value) or await agetval(value)`"""


def getval(value: _T | None) -> _T:
    """
    Returns value if value is not None\n
    Raised:
        - `NoneValueError`
    """
    if value is None:
        raise NoneValueError

    return value


def qualname(obj: object) -> str:
    if isclass(obj):
        return obj.__qualname__

    return obj.__class__.__qualname__
