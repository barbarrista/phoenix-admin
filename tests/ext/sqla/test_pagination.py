import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from types import SimpleNamespace
from typing import cast

import pytest
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.dto import PaginationParamsDTO
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from starlette.requests import Request
from starlette.types import Scope


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "item"

    id: Mapped[str] = mapped_column(primary_key=True)


class ItemView(SqlalchemyModelView[Item]):
    identity = "item"
    pk_field = Pk(Item.id)
    __config__ = ModelViewConfig(page_limit=2, max_page_limit=3)
    fields = ()


def test_max_page_limit_defaults_to_100() -> None:
    assert ModelViewConfig().max_page_limit == 100  # noqa: PLR2004


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def seed_items(session: AsyncSession) -> list[Item]:
    items = [Item(id=item_id) for item_id in "abcde"]
    session.add_all(items)
    await session.flush()
    return items


def api_request(query: str, session: AsyncSession | None = None) -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/api/item",
        "query_string": query.encode(),
        "headers": [],
        "app": SimpleNamespace(
            state=SimpleNamespace(app_state=SimpleNamespace(model_view_registry={})),
        ),
    }
    request = Request(cast("Scope", scope))
    if session is not None:
        request.state.db_session = session
    return request


def ids_of(rows: list[Item]) -> list[str]:
    return [row.id for row in rows]


async def missing_limit_uses_page_limit() -> None:
    async with open_session() as session:
        items = await seed_items(session)
        view = ItemView()
        ordered = sorted(item.id for item in items)
        stmt = await view.get_list_stmt()

        page = list(
            await view.get_list(
                stmt,
                session=session,
                dto=PaginationParamsDTO(),
            )
        )
        response = await view.handle_api_request(api_request("", session))
        body = json.loads(bytes(response.body))

        assert ids_of(page) == ordered[: view.config.page_limit]
        assert response.status_code == HTTPStatus.OK
        assert len(body["results"]) == view.config.page_limit
        assert body["count"] == len(items)


async def non_numeric_limit_uses_page_limit() -> None:
    async with open_session() as session:
        items = await seed_items(session)
        view = ItemView()
        response = await view.handle_api_request(api_request("limit=abc", session))
        body = json.loads(bytes(response.body))

        assert response.status_code == HTTPStatus.OK
        assert len(body["results"]) == view.config.page_limit
        assert body["count"] == len(items)


async def rejected_pagination(query: str) -> tuple[int, str]:
    view = ItemView()
    response = await view.handle_api_request(api_request(query))
    body = json.loads(bytes(response.body))
    detail = body["detail"]
    assert isinstance(detail, str)
    return response.status_code, detail


async def requested_limit_is_capped() -> None:
    async with open_session() as session:
        items = await seed_items(session)
        view = ItemView()
        ordered = sorted(item.id for item in items)
        stmt = await view.get_list_stmt()
        above_max = view.config.max_page_limit + 1

        capped = list(
            await view.get_list(
                stmt,
                session=session,
                dto=PaginationParamsDTO(limit=above_max),
            )
        )
        response = await view.handle_api_request(
            api_request(f"limit={above_max}", session),
        )
        body = json.loads(bytes(response.body))
        single = list(
            await view.get_list(
                stmt,
                session=session,
                dto=PaginationParamsDTO(limit=1),
            )
        )

        assert len(items) > view.config.max_page_limit
        assert ids_of(capped) == ordered[: view.config.max_page_limit]
        assert response.status_code == HTTPStatus.OK
        assert len(body["results"]) == view.config.max_page_limit
        assert body["count"] == len(items)
        assert ids_of(single) == ordered[:1]


def test_missing_limit_uses_page_limit() -> None:
    asyncio.run(missing_limit_uses_page_limit())


def test_non_numeric_limit_uses_page_limit() -> None:
    asyncio.run(non_numeric_limit_uses_page_limit())


@pytest.mark.parametrize(
    ("query", "mentioned"),
    [
        ("limit=0", "limit"),
        ("limit=-5", "limit"),
        ("offset=-1", "offset"),
    ],
)
def test_out_of_range_pagination_returns_400(query: str, mentioned: str) -> None:
    status_code, detail = asyncio.run(rejected_pagination(query))

    assert status_code == HTTPStatus.BAD_REQUEST
    assert mentioned in detail


def test_requested_limit_is_capped() -> None:
    asyncio.run(requested_limit_is_capped())
