from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import cast

import pytest
import pytest_asyncio
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.dto import PaginationParamsDTO
from phoenix_admin.ext.sqla.fields import RelationshipField
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.utils import get_default_load_strategy
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    DeclarativeBase,
    Load,
    Mapped,
    mapped_column,
    relationship,
    selectinload,
)
from tests.ext.sqla.session import open_session, record_sql


class Base(DeclarativeBase):
    pass


class Subdivision(Base):
    __tablename__ = "subdivision"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    subdivision_id: Mapped[int | None] = mapped_column(ForeignKey("subdivision.id"))
    subdivision: Mapped[Subdivision | None] = relationship()


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))


class Award(Base):
    __tablename__ = "award"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))


class Author(Base):
    __tablename__ = "author"

    id: Mapped[int] = mapped_column(primary_key=True)
    books: Mapped[list[Book]] = relationship()
    awards: Mapped[list[Award]] = relationship()


class UserView(SqlalchemyModelView[User]):
    identity = "user"
    pk_field = Pk(User.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields = (RelationshipField(identity="subdivision", source_field=User.subdivision),)


def _selectin_subdivision() -> Load:
    return cast("Load", selectinload(User.subdivision))


class SelectinUserView(UserView):
    identity = "user-selectin"
    fields = (
        RelationshipField(
            identity="subdivision",
            source_field=User.subdivision,
            load_strategy=_selectin_subdivision,
        ),
    )


class AuthorView(SqlalchemyModelView[Author]):
    identity = "author"
    pk_field = Pk(Author.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields = (
        RelationshipField(identity="book", source_field=Author.books),
        RelationshipField(identity="award", source_field=Author.awards),
    )


class ColumnUserView(UserView):
    identity = "user-column"
    fields = (RelationshipField(identity="id", source_field=User.id),)


def select_statements(statements: list[str]) -> list[str]:
    return [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
    ]


@dataclass(frozen=True, slots=True)
class AuthorRows:
    authors: tuple[Author, Author]
    books: tuple[tuple[Book, ...], tuple[Book, ...]]
    awards: tuple[tuple[Award, ...], tuple[Award, ...]]


@dataclass(frozen=True, slots=True)
class UserRows:
    subdivision: Subdivision
    users: tuple[User, ...]


async def seed_authors(session: AsyncSession) -> AuthorRows:
    first = Author(id=1)
    second = Author(id=2)
    authors = (first, second)
    books = (
        (Book(id=1, author_id=first.id), Book(id=2, author_id=first.id)),
        (Book(id=3, author_id=second.id),),
    )
    awards = (
        (
            Award(id=1, author_id=first.id),
            Award(id=2, author_id=first.id),
            Award(id=3, author_id=first.id),
        ),
        (Award(id=4, author_id=second.id), Award(id=5, author_id=second.id)),
    )
    session.add_all([*authors, *books[0], *books[1], *awards[0], *awards[1]])
    await session.flush()
    return AuthorRows(authors=authors, books=books, awards=awards)


async def seed_hq_users(session: AsyncSession) -> UserRows:
    subdivision = Subdivision(id=1, name="hq")
    users = (User(id=1, subdivision=subdivision), User(id=2))
    session.add_all([subdivision, *users])
    await session.flush()
    return UserRows(subdivision=subdivision, users=users)


async def seed_user_in_hq(session: AsyncSession) -> UserRows:
    subdivision = Subdivision(id=1, name="hq")
    users = (User(id=1, subdivision=subdivision),)
    session.add_all([subdivision, *users])
    await session.flush()
    return UserRows(subdivision=subdivision, users=users)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with open_session(Base) as session:
        yield session


@pytest_asyncio.fixture
async def statements(session: AsyncSession) -> list[str]:
    return record_sql(session)


@pytest_asyncio.fixture
async def authors(session: AsyncSession, statements: list[str]) -> AuthorRows:
    rows = await seed_authors(session)
    statements.clear()
    return rows


@pytest_asyncio.fixture
async def hq_users(session: AsyncSession, statements: list[str]) -> UserRows:
    rows = await seed_hq_users(session)
    statements.clear()
    return rows


@pytest_asyncio.fixture
async def user_in_hq(session: AsyncSession, statements: list[str]) -> UserRows:
    rows = await seed_user_in_hq(session)
    statements.clear()
    return rows


@pytest.mark.asyncio
async def test_two_collections_do_not_duplicate_rows(
    session: AsyncSession,
    statements: list[str],
    authors: AuthorRows,
) -> None:
    view = AuthorView()
    stmt = await view._apply_load_strategies(await view.get_list_stmt())  # noqa: SLF001
    rows = list(
        await view.get_list(
            stmt,
            session=session,
            dto=PaginationParamsDTO(),
        )
    )
    by_id = {row.id: row for row in rows}
    selects = select_statements(statements)
    first, second = authors.authors
    parent, *collections = selects

    assert [row.id for row in rows] == [author.id for author in authors.authors]
    assert len(by_id[first.id].books) == len(authors.books[0])
    assert len(by_id[first.id].awards) == len(authors.awards[0])
    assert len(by_id[second.id].books) == len(authors.books[1])
    assert len(by_id[second.id].awards) == len(authors.awards[1])
    assert await view.get_count(stmt, session) == len(authors.authors)
    assert "JOIN" not in parent.upper()
    assert len(collections) == len(view.fields)
    assert all(" IN " in statement.upper() for statement in collections)


@pytest.mark.asyncio
async def test_many_to_one_uses_one_joinedload(
    session: AsyncSession,
    statements: list[str],
    hq_users: UserRows,
) -> None:
    view = UserView()
    stmt = await view._apply_load_strategies(await view.get_list_stmt())  # noqa: SLF001
    rows = list(
        await view.get_list(
            stmt,
            session=session,
            dto=PaginationParamsDTO(),
        )
    )
    selects = select_statements(statements)
    joined, *extra = selects

    assert [row.id for row in rows] == [user.id for user in hq_users.users]
    assert rows[0].subdivision is not None
    assert rows[0].subdivision.name == hq_users.subdivision.name
    assert rows[1].subdivision is None
    assert extra == []
    assert "JOIN" in joined.upper()


@pytest.mark.asyncio
async def test_explicit_load_strategy_replaces_default(
    session: AsyncSession,
    statements: list[str],
    user_in_hq: UserRows,
) -> None:
    view = SelectinUserView()
    stmt = await view._apply_load_strategies(await view.get_list_stmt())  # noqa: SLF001
    rows = list(
        await view.get_list(
            stmt,
            session=session,
            dto=PaginationParamsDTO(),
        )
    )
    parent, follow_up = select_statements(statements)

    assert rows[0].subdivision is not None
    assert rows[0].subdivision.name == user_in_hq.subdivision.name
    assert "JOIN" not in parent.upper()
    assert " IN " in follow_up.upper()


@pytest.mark.asyncio
async def test_column_relationship_field_is_rejected() -> None:
    view = ColumnUserView()

    with pytest.raises(TypeError, match=r"User\.id"):
        await view._apply_load_strategies(select(User))  # noqa: SLF001

    with pytest.raises(TypeError, match="relationship"):
        get_default_load_strategy(User.id)
