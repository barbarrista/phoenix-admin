from typing import Any, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    ColumnProperty,
    InstrumentedAttribute,
    Load,
    RelationshipDirection,
    RelationshipProperty,
    joinedload,
    selectinload,
)
from starlette.requests import Request

from phoenix_admin.ext.sqla.extension import SqlalchemyAsyncSessionExtension
from phoenix_admin.utils import qualname

_DB_SESSION_FIELD_NAME = "db_session"
_T = TypeVar("_T")


def get_db_session(request: Request) -> AsyncSession:
    session = getattr(request.state, _DB_SESSION_FIELD_NAME, None)
    if session is None:
        msg = f"{_DB_SESSION_FIELD_NAME} is not defined. May be you forgot add {qualname(SqlalchemyAsyncSessionExtension)} to extensions?"
        raise ValueError(msg)

    return cast("AsyncSession", session)


def get_field_name(field: str | InstrumentedAttribute[Any]) -> str:
    if isinstance(field, str):
        return field

    return field.key


def why_source_rejects_none(
    source: str | InstrumentedAttribute[Any] | None,
    *,
    required: bool,
) -> str | None:
    if required:
        return "the field is declared with required=True, but its value is None"

    if not isinstance(source, InstrumentedAttribute):
        return "source_field is not a mapped attribute, so None is not accepted"

    prop = source.property
    if isinstance(prop, ColumnProperty):
        return _column_none_reason(prop)

    if isinstance(prop, RelationshipProperty):
        return _relationship_none_reason(prop)

    return "the field does not accept None"


def is_source_optional(
    source: str | InstrumentedAttribute[Any] | None,
    *,
    required: bool,
) -> bool:
    return why_source_rejects_none(source, required=required) is None


def _column_none_reason(prop: ColumnProperty[_T]) -> str | None:
    if all(column.nullable for column in prop.columns):
        return None

    return "the column is not nullable, but its value is None"


def _relationship_none_reason(prop: RelationshipProperty[_T]) -> str | None:
    if prop.direction is not RelationshipDirection.MANYTOONE:
        return "the relationship is not optional, but its value is None"

    if all(column.nullable for column in prop.local_columns):
        return None

    return "the foreign key is not nullable, but its value is None"


def get_default_load_strategy(field: InstrumentedAttribute[Any]) -> Load:
    prop = field.property
    if not isinstance(prop, RelationshipProperty):
        msg = (
            f"{field} is not a relationship. "
            "RelationshipField.source_field must point at a relationship attribute."
        )
        raise TypeError(msg)

    if prop.uselist is True:
        return cast("Load", selectinload(field))

    return cast("Load", joinedload(field))
