from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    InstrumentedAttribute,
    Load,
    RelationshipProperty,
    joinedload,
    selectinload,
)
from starlette.requests import Request

from phoenix_admin.ext.sqla.extension import SqlalchemyAsyncSessionExtension
from phoenix_admin.utils import qualname

_DB_SESSION_FIELD_NAME = "db_session"


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
