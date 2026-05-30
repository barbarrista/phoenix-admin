import datetime
from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, TypeAlias, TypeVar

from phoenix_admin.fields.exceptions import ParseError, try_cast
from phoenix_admin.utils import getval

MapStrategy: TypeAlias = Literal["name_as_value", "value"]


class BaseFieldMapper:
    def to_json(self, value: Any, *, is_optional: bool = False) -> Any:  # noqa: ANN401
        raise NotImplementedError

    def from_json(self, value: Any, *, is_optional: bool = False) -> Any:  # noqa: ANN401
        raise NotImplementedError


class TextFieldMapper(BaseFieldMapper):
    def to_json(self, value: Any, *, is_optional: bool = False) -> str | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        return str(value)

    def from_json(self, value: Any, *, is_optional: bool = False) -> str | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        return str(value)


class EmailFieldMapper(TextFieldMapper):
    pass


class PasswordFieldMapper(TextFieldMapper):
    pass


class FloatFieldMapper(BaseFieldMapper):
    def to_json(
        self, value: float | None, *, is_optional: bool = False
    ) -> float | None:
        if is_optional and value is None:
            return None
        return value

    def from_json(self, value: Any, *, is_optional: bool = False) -> float | None:  # noqa: ANN401
        if is_optional and value is None:
            return None
        return try_cast(float, value)


class IntegerFieldMapper(BaseFieldMapper):
    def to_json(self, value: int | None, *, is_optional: bool = False) -> int | None:
        if is_optional and value is None:
            return None
        return value

    def from_json(self, value: Any, *, is_optional: bool = False) -> int | None:  # noqa: ANN401
        if is_optional and value is None:
            return None
        return try_cast(int, value)


class DecimalFieldMapper(BaseFieldMapper):
    def to_json(
        self,
        value: Decimal | None,
        *,
        is_optional: bool = False,
    ) -> str | None:
        if is_optional and value is None:
            return None
        return str(value)

    def from_json(self, value: Any, *, is_optional: bool = False) -> Decimal | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        return try_cast(Decimal, value)


class SelectFieldMapper(TextFieldMapper):
    pass


class EnumFieldMapper(BaseFieldMapper):
    def __init__(
        self,
        enum_cls: type[Enum],
        map_strategy: MapStrategy,
    ) -> None:
        self._enum_cls = enum_cls
        self._map_strategy = map_strategy

    def to_json(self, value: Enum | None, *, is_optional: bool = False) -> Any:  # noqa: ANN401
        if is_optional and value is None:
            return None

        value = getval(value, exc=ParseError("Got unexpected None value"))
        if self._map_strategy == "name_as_value":
            return value.name

        return value.value

    def from_json(self, value: Any, *, is_optional: bool = False) -> Enum | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        try:
            if self._map_strategy == "name_as_value":
                return self._enum_cls[value]

            return self._enum_cls(value)
        except (KeyError, ValueError) as exc:
            raise ParseError from exc


class TextAreaFieldMapper(TextFieldMapper):
    pass


class CheckboxFieldMapper(BaseFieldMapper):
    def to_json(self, value: bool | None, *, is_optional: bool = False) -> str | None:  # noqa: FBT001
        if is_optional and value is None:
            return None
        return str(value).lower()

    def from_json(self, value: str | None, *, is_optional: bool = False) -> bool | None:
        if is_optional and value is None:
            return None

        value = _getval(value)
        if value == "true":
            return True

        if value == "false":
            return False

        msg = f"Unexpected value: {value}"
        raise ValueError(msg)


class HiddenFieldMapper(TextFieldMapper):
    pass


class ListFieldMapper(BaseFieldMapper):
    def __init__(self, child_mapper: BaseFieldMapper) -> None:
        self._child_mapper = child_mapper

    def to_json(
        self,
        value: Sequence[Any] | None,
        *,
        is_optional: bool = False,
    ) -> Sequence[Any] | None:
        if is_optional and value is None:
            return None

        return [self._child_mapper.to_json(item) for item in _getval(value)]

    def from_json(
        self,
        value: Sequence[Any] | None,
        *,
        is_optional: bool = False,
    ) -> Sequence[Any] | None:
        if is_optional and value is None:
            return None

        value = _getval(value)
        return [self._child_mapper.from_json(item) for item in value]


class DateFieldMapper(BaseFieldMapper):
    def __init__(
        self,
        dump_format: str | None = None,
    ) -> None:
        self._dump_format = dump_format

    def to_json(self, value: date | None, *, is_optional: bool = False) -> str | None:
        if is_optional and value is None:
            return None

        value = _getval(value)
        if self._dump_format is not None:
            try:
                return value.strftime(self._dump_format)
            except (ValueError, TypeError) as exc:
                raise ParseError from exc

        return value.isoformat()

    def from_json(
        self,
        value: str | None,
        *,
        is_optional: bool = False,
    ) -> datetime.date | None:
        if is_optional and value is None:
            return None

        try:
            return datetime.date.fromisoformat(value)  # type:ignore[arg-type]
        except (ValueError, TypeError) as exc:
            raise ParseError from exc


class DateTimeMapper(BaseFieldMapper):
    def __init__(
        self,
        dump_format: str | None = None,
    ) -> None:
        self._dump_format = dump_format

    def to_json(
        self,
        value: datetime.datetime | None,
        *,
        is_optional: bool = False,
    ) -> str | None:
        if is_optional and value is None:
            return None

        value = _getval(value)
        if self._dump_format is not None:
            try:
                return value.strftime(self._dump_format)
            except (ValueError, TypeError) as exc:
                raise ParseError from exc

        return value.isoformat()

    def from_json(
        self,
        value: str | None,
        *,
        is_optional: bool = False,
    ) -> datetime.date | None:
        if is_optional and value is None:
            return None

        value = _getval(value)
        try:
            return datetime.datetime.fromisoformat(value).replace(tzinfo=UTC)
        except (ValueError, TypeError) as exc:
            raise ParseError from exc


_T = TypeVar("_T")


def _getval(value: _T | None) -> _T:
    return getval(value, exc=ParseError("Got unexpected None value"))
