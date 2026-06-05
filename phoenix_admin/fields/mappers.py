import datetime
from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NotRequired,
    TypeAlias,
    TypedDict,
    TypeVar,
    Unpack,
)

from phoenix_admin.fields.exceptions import ParseError, try_cast
from phoenix_admin.utils import getval

if TYPE_CHECKING:
    from phoenix_admin.ext.sqla.view import SqlalchemyModelView

_T = TypeVar("_T")


class FieldMapperKwargs(TypedDict):
    model_view: NotRequired["SqlalchemyModelView[Any]"]


MapStrategy: TypeAlias = Literal["name_as_value", "value"]


class BaseFieldMapper:
    async def to_json(
        self,
        value: Any,  # noqa: ANN401
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],
    ) -> Any:  # noqa: ANN401
        raise NotImplementedError

    async def from_json(self, value: Any, *, is_optional: bool = False) -> Any:  # noqa: ANN401
        raise NotImplementedError

    def to_html(
        self,
        value: Any,  # noqa: ANN401
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str:
        if value is None:
            return "-"

        return str(value)

    @staticmethod
    def _getval(value: _T | None) -> _T:
        return getval(value, exc=ParseError("Got unexpected None value"))


class TextFieldMapper(BaseFieldMapper):
    async def to_json(
        self,
        value: Any,  # noqa: ANN401
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return str(value)

    async def from_json(self, value: Any, *, is_optional: bool = False) -> str | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return str(value)


class EmailFieldMapper(TextFieldMapper):
    def to_html(
        self,
        value: Any,  # noqa: ANN401
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str:
        if value is None:
            return "-"

        return f"<a href='mailto:{value}'>{value}</a>"


class PasswordFieldMapper(TextFieldMapper):
    pass


class FloatFieldMapper(BaseFieldMapper):
    async def to_json(
        self,
        value: float | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> float | None:
        if is_optional and value is None:
            return None

        return self._getval(value)

    async def from_json(self, value: Any, *, is_optional: bool = False) -> float | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return try_cast(float, value)


class IntegerFieldMapper(BaseFieldMapper):
    async def to_json(
        self,
        value: int | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> int | None:
        if is_optional and value is None:
            return None

        return self._getval(value)

    async def from_json(self, value: Any, *, is_optional: bool = False) -> int | None:  # noqa: ANN401
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return try_cast(int, value)


class DecimalFieldMapper(BaseFieldMapper):
    async def to_json(
        self,
        value: Decimal | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return str(value)

    async def from_json(
        self,
        value: Any,  # noqa: ANN401
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> Decimal | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
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

    async def to_json(
        self,
        value: Enum | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> Any:  # noqa: ANN401
        if is_optional and value is None:
            return None

        value = self._getval(value)
        if self._map_strategy == "name_as_value":
            return value.name

        return value.value

    async def from_json(
        self,
        value: Any,  # noqa: ANN401
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> Enum | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        try:
            if self._map_strategy == "name_as_value":
                return self._enum_cls[value]

            return self._enum_cls(value)
        except (KeyError, ValueError) as exc:
            raise ParseError from exc


class TextAreaFieldMapper(TextFieldMapper):
    pass


class BooleanFieldMapper(BaseFieldMapper):
    async def to_json(
        self,
        value: bool | None,  # noqa: FBT001
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return str(value).lower()

    async def from_json(
        self, value: str | None, *, is_optional: bool = False
    ) -> bool | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        if value == "true":
            return True

        if value == "false":
            return False

        msg = f"Unexpected value: {value}"
        raise ValueError(msg)

    def to_html(self, value: Any, **kwargs: FieldMapperKwargs) -> str:  # noqa: ANN401, ARG002
        if value is None:
            return "-"

        return "✅" if value == "true" else "❌"


class HiddenFieldMapper(TextFieldMapper):
    pass


class ListFieldMapper(BaseFieldMapper):
    def __init__(self, child_mapper: BaseFieldMapper) -> None:
        self._child_mapper = child_mapper

    async def to_json(
        self,
        value: Sequence[Any] | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> Sequence[Any] | None:
        if is_optional and value is None:
            return None

        return [self._child_mapper.to_json(item) for item in self._getval(value)]

    async def from_json(
        self,
        value: Sequence[Any] | None,
        *,
        is_optional: bool = False,
    ) -> Sequence[Any] | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        return [self._child_mapper.from_json(item) for item in value]


class DateFieldMapper(BaseFieldMapper):
    def __init__(
        self,
        dump_format: str | None = None,
    ) -> None:
        self._dump_format = dump_format

    async def to_json(
        self,
        value: date | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        if self._dump_format is not None:
            try:
                return value.strftime(self._dump_format)
            except (ValueError, TypeError) as exc:
                raise ParseError from exc

        return value.isoformat()

    async def from_json(
        self,
        value: str | None,
        *,
        is_optional: bool = False,
    ) -> datetime.date | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        try:
            return datetime.date.fromisoformat(value)
        except (ValueError, TypeError) as exc:
            raise ParseError from exc


class DateTimeMapper(BaseFieldMapper):
    def __init__(
        self,
        dump_format: str | None = None,
    ) -> None:
        self._dump_format = dump_format

    async def to_json(
        self,
        value: datetime.datetime | None,
        *,
        is_optional: bool = False,
        **kwargs: Unpack[FieldMapperKwargs],  # noqa: ARG002
    ) -> str | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        if self._dump_format is not None:
            try:
                return value.strftime(self._dump_format)
            except (ValueError, TypeError) as exc:
                raise ParseError from exc

        return value.isoformat()

    async def from_json(
        self,
        value: str | None,
        *,
        is_optional: bool = False,
    ) -> datetime.date | None:
        if is_optional and value is None:
            return None

        value = self._getval(value)
        try:
            return datetime.datetime.fromisoformat(value).replace(tzinfo=UTC)
        except (ValueError, TypeError) as exc:
            raise ParseError from exc
