from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession
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
