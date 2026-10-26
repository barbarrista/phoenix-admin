from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


@asynccontextmanager
async def open_session(base: type[DeclarativeBase]) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def record_sql(session: AsyncSession) -> list[str]:
    bind = session.bind
    if not isinstance(bind, AsyncEngine):
        msg = "Session is not bound to an async engine"
        raise TypeError(msg)

    statements: list[str] = []

    def before_cursor_execute(*args: object) -> None:
        statement = args[2]
        if not isinstance(statement, str):
            msg = "SQL statement must be a string"
            raise TypeError(msg)
        statements.append(statement)

    event.listen(bind.sync_engine, "before_cursor_execute", before_cursor_execute)
    return statements
