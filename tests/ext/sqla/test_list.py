import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.dto import PaginationParamsDTO
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from sqlalchemy import ForeignKey, Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    joinedload,
    mapped_column,
    relationship,
)


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
    items = [
        Item(id="c", name="z"),
        Item(id="a", name="m"),
        Item(id="b", name="n"),
    ]
    session.add_all(items)
    await session.flush()
    return items


def ids_of(rows: Sequence[Item]) -> list[str]:
    return [row.id for row in rows]


async def pages_cover_every_row_once() -> None:
    async with open_session() as session:
        await seed_items(session)
        view = ItemView()
        stmt = await view.get_list_stmt()
        page_limit = view.config.page_limit

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

        assert ids_of(first) == ["a", "b"]
        assert ids_of(second) == ["c"]
        assert await view.get_count(stmt, session) == len(
            ids_of(first) + ids_of(second)
        )


async def first_page_repeats_in_the_same_order() -> None:
    async with open_session() as session:
        await seed_items(session)
        view = ItemView()
        stmt = await view.get_list_stmt()
        dto = PaginationParamsDTO(offset=0)

        first = await view.get_list(stmt, session=session, dto=dto)
        again = await view.get_list(stmt, session=session, dto=dto)

        assert ids_of(again) == ids_of(first) == ["a", "b"]


async def explicit_order_by_is_kept() -> None:
    async with open_session() as session:
        await seed_items(session)
        view = NameOrderedItemView()
        stmt = await view.get_list_stmt()

        page = await view.get_list(
            stmt,
            session=session,
            dto=PaginationParamsDTO(offset=0),
        )

        assert ids_of(page) == ["c", "b"]


async def count_is_parents_not_join_pairs() -> None:
    async with open_session() as session:
        parent_a = Parent(id=1)
        parent_b = Parent(id=2)
        parent_without_children = Parent(id=3)
        parents_with_children = [parent_a, parent_b]
        session.add_all(
            [
                *parents_with_children,
                parent_without_children,
                Child(id=1, parent=parent_a),
                Child(id=2, parent=parent_a),
                Child(id=3, parent=parent_b),
            ]
        )
        await session.flush()

        view = JoinedParentView()
        stmt = await view.get_list_stmt()

        assert await view.get_count(stmt, session) == len(parents_with_children)


async def count_ignores_limit_offset_and_order() -> None:
    async with open_session() as session:
        items = await seed_items(session)
        view = LimitedItemView()
        stmt = await view.get_list_stmt()

        assert await view.get_count(stmt, session) == len(items)


async def count_keeps_where_clause() -> None:
    async with open_session() as session:
        items = [
            Item(id="a", name="visible"),
            Item(id="b", name="hidden"),
            Item(id="c", name="visible"),
        ]
        session.add_all(items)
        await session.flush()
        view = FilteredItemView()
        stmt = await view.get_list_stmt()
        visible = [item for item in items if item.name != "hidden"]

        assert await view.get_count(stmt, session) == len(visible)


async def count_ignores_loader_options() -> None:
    async with open_session() as session:
        parent = Parent(id=1)
        session.add_all(
            [
                parent,
                Child(id=1, parent=parent),
                Child(id=2, parent=parent),
            ]
        )
        await session.flush()
        view = LoadedParentView()
        stmt = await view.get_list_stmt()

        assert await view.get_count(stmt, session) == 1


def test_pages_cover_every_row_once() -> None:
    asyncio.run(pages_cover_every_row_once())


def test_first_page_repeats_in_the_same_order() -> None:
    asyncio.run(first_page_repeats_in_the_same_order())


def test_explicit_order_by_is_kept() -> None:
    asyncio.run(explicit_order_by_is_kept())


def test_count_is_parents_not_join_pairs() -> None:
    asyncio.run(count_is_parents_not_join_pairs())


def test_count_ignores_limit_offset_and_order() -> None:
    asyncio.run(count_ignores_limit_offset_and_order())


def test_count_keeps_where_clause() -> None:
    asyncio.run(count_keeps_where_clause())


def test_count_ignores_loader_options() -> None:
    asyncio.run(count_ignores_loader_options())
