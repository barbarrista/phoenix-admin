from typing import Any, TypeVar, cast

_T = TypeVar("_T", bound=Any)


class ParseError(Exception):
    def __init__(self, message: str | None = None) -> None:
        self.message = message
        super().__init__(message)


def try_cast(cls: type[_T], value: Any) -> _T:  # noqa: ANN401
    try:
        return cast("_T", cls(value))
    except Exception as exc:
        raise ParseError from exc
