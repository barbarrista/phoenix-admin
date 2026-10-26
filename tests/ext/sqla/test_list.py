from collections.abc import AsyncIterator, Sequence

import pytest
import pytest_asyncio
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.dto import PaginationParamsDTO
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from sqlalchemy import ForeignKey, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    joinedload,
    mapped_column,
    relationship,
)
from tests.ext.sqla.session import open_session


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "item"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


class Parent(Base):
    __tablename__ = "parent"

    id: Mapped[int] = mapped_column(primary_key=True)
    children: Mapped[list["Child"]] = relationship(back_populates="parent")


class Child(Base):
    __tablename__ = "child"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent.id"))
    parent: Mapped[Parent] = relationship(back_populates="children")


class ItemView(SqlalchemyModelView[Item]):
    identity = "item"
    pk_field = Pk(Item.id)
    __config__ = ModelViewConfig(page_limit=2)
    fields = ()


class NameOrderedItemView(ItemView):
    identity = "item-by-name"

    async def get_list_stmt(self) -> Select[tuple[Item]]:
        return select(Item).order_by(Item.name.desc())


class LimitedItemView(ItemView):
    identity = "limited-item"

    async def get_list_stmt(self) -> Select[tuple[Item]]:
        return select(Item).order_by(Item.name.desc()).limit(1).offset(1)


class FilteredItemView(ItemView):
    identity = "filtered-item"

    async def get_list_stmt(self) -> Select[tuple[Item]]:
        return select(Item).where(Item.name != "hidden")


class JoinedParentView(SqlalchemyModelView[Parent]):
    identity = "parent"
    pk_field = Pk(Parent.id)
    __config__ = ModelViewConfig(page_limit=2)
    fields = ()

    async def get_list_stmt(self) -> Select[tuple[Parent]]:
        return select(Parent).join(Child.parent)


class LoadedParentView(SqlalchemyModelView[Parent]):
    identity = "loaded-parent"
    pk_field = Pk(Parent.id)
    __config__ = ModelViewConfig(page_limit=2)
    fields = ()

    async def get_list_stmt(self) -> Select[tuple[Parent]]:
        return select(Parent).options(joinedload(Parent.children))


async def seed_items(session: AsyncSession) -> list[Item]:
    items = [
        Item(id="c", name="z"),
        Item(id="a", name="m"),
        Item(id="b", name="n"),
    ]
    session.add_all(items)
    await session.flush()
    return items


async def seed_joined_parents(session: AsyncSession) -> tuple[Parent, ...]:
    parent_a = Parent(id=1)
    parent_b = Parent(id=2)
    with_children = (parent_a, parent_b)
    session.add_all(
        [
            *with_children,
            Parent(id=3),
            Child(id=1, parent=parent_a),
            Child(id=2, parent=parent_a),
            Child(id=3, parent=parent_b),
        ]
    )
    await session.flush()
    return with_children


async def seed_visible_items(session: AsyncSession) -> list[Item]:
    items = [
        Item(id="a", name="visible"),
        Item(id="b", name="hidden"),
        Item(id="c", name="visible"),
    ]
    session.add_all(items)
    await session.flush()
    return items


async def seed_parent_with_children(session: AsyncSession) -> Parent:
    parent = Parent(id=1)
    session.add_all([parent, Child(id=1, parent=parent), Child(id=2, parent=parent)])
    await session.flush()
    return parent


def ids_of(rows: Sequence[Item]) -> list[str]:
    return [row.id for row in rows]


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with open_session(Base) as session:
        yield session


@pytest_asyncio.fixture
async def items(session: AsyncSession) -> list[Item]:
    return await seed_items(session)


@pytest_asyncio.fixture
async def parents_with_children(session: AsyncSession) -> tuple[Parent, ...]:
    return await seed_joined_parents(session)


@pytest_asyncio.fixture
async def visible_items(session: AsyncSession) -> list[Item]:
    return await seed_visible_items(session)


@pytest_asyncio.fixture
async def parent_with_children(session: AsyncSession) -> Parent:
    return await seed_parent_with_children(session)


@pytest.mark.asyncio
async def test_pages_cover_every_row_once(
    session: AsyncSession,
    items: list[Item],
) -> None:
    view = ItemView()
    stmt = await view.get_list_stmt()
    page_limit = view.config.page_limit
    ordered = sorted(item.id for item in items)

    first = await view.get_list(
        stmt,
        session=session,
        dto=PaginationParamsDTO(offset=0),
    )
    second = await view.get_list(
        stmt,
        session=session,
        dto=PaginationParamsDTO(offset=page_limit),
    )

    assert ids_of(first) == ordered[:page_limit]
    assert ids_of(second) == ordered[page_limit:]
    assert await view.get_count(stmt, session) == len(items)


@pytest.mark.asyncio
async def test_first_page_repeats_in_the_same_order(
    session: AsyncSession,
    items: list[Item],
) -> None:
    view = ItemView()
    stmt = await view.get_list_stmt()
    dto = PaginationParamsDTO(offset=0)
    ordered = sorted(item.id for item in items)

    first = await view.get_list(stmt, session=session, dto=dto)
    again = await view.get_list(stmt, session=session, dto=dto)

    assert ids_of(again) == ids_of(first) == ordered[: view.config.page_limit]


@pytest.mark.asyncio
async def test_explicit_order_by_is_kept(
    session: AsyncSession,
    items: list[Item],
) -> None:
    view = NameOrderedItemView()
    stmt = await view.get_list_stmt()
    ordered = sorted(items, key=lambda item: item.name, reverse=True)

    page = await view.get_list(
        stmt,
        session=session,
        dto=PaginationParamsDTO(offset=0),
    )

    assert ids_of(page) == [item.id for item in ordered[: view.config.page_limit]]


@pytest.mark.asyncio
async def test_count_is_parents_not_join_pairs(
    session: AsyncSession,
    parents_with_children: tuple[Parent, ...],
) -> None:
    view = JoinedParentView()
    stmt = await view.get_list_stmt()

    assert await view.get_count(stmt, session) == len(parents_with_children)


@pytest.mark.asyncio
async def test_count_ignores_limit_offset_and_order(
    session: AsyncSession,
    items: list[Item],
) -> None:
    view = LimitedItemView()
    stmt = await view.get_list_stmt()

    assert await view.get_count(stmt, session) == len(items)


@pytest.mark.asyncio
async def test_count_keeps_where_clause(
    session: AsyncSession,
    visible_items: list[Item],
) -> None:
    view = FilteredItemView()
    stmt = await view.get_list_stmt()
    visible = [item for item in visible_items if item.name != "hidden"]

    assert await view.get_count(stmt, session) == len(visible)


@pytest.mark.asyncio
@pytest.mark.usefixtures("parent_with_children")
async def test_count_ignores_loader_options(session: AsyncSession) -> None:
    view = LoadedParentView()
    stmt = await view.get_list_stmt()

    assert await view.get_count(stmt, session) == 1
