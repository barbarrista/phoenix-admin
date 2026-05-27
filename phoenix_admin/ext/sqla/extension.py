from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from phoenix_admin.extensions.extension import OnRequestExtension


class SqlalchemyAsyncSessionExtension(OnRequestExtension):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._factory = factory

    @asynccontextmanager
    async def on_request(self, request: Request) -> AsyncGenerator[None]:
        async with self._factory() as session:
            request.state.db_session = session
            yield
