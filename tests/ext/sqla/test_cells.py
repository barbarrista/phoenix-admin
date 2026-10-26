from collections.abc import Sequence
from types import SimpleNamespace
from typing import ClassVar, cast

import pytest
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from phoenix_admin.fields.fields import (
    BaseField,
    BooleanField,
    EmailField,
    FileField,
    ListField,
    TextField,
)
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from starlette.requests import Request
from starlette.types import Scope


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column()
    email: Mapped[str | None] = mapped_column()
    attachment: Mapped[str | None] = mapped_column()
    nickname: Mapped[str | None] = mapped_column()
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column()


class PersonView(SqlalchemyModelView[Person]):
    identity = "person"
    pk_field = Pk(Person.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields: ClassVar[Sequence[BaseField]] = ()


class NameView(PersonView):
    fields = (TextField(source_field=Person.name),)


class EmailView(PersonView):
    fields = (EmailField(source_field=Person.email),)


class FileView(PersonView):
    fields = (
        FileField(source_field=Person.attachment),
        TextField(source_field=Person.nickname),
    )


class TagView(PersonView):
    fields = (ListField(child_field=TextField(), source_field=Person.tags),)


class ActiveView(PersonView):
    fields = (BooleanField(source_field=Person.active),)


def grid_request() -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "app": SimpleNamespace(
            state=SimpleNamespace(app_state=SimpleNamespace(model_view_registry={})),
        ),
    }
    return Request(cast("Scope", scope))


def make_person(
    *,
    name: str | None = "<b>x</b>",
    email: str | None = 'a"@b.com',
    attachment: str | None = "<script>",
    nickname: str | None = "nick",
    tags: list[str] | None = None,
    active: bool = True,
) -> Person:
    return Person(
        id=1,
        name=name,
        email=email,
        attachment=attachment,
        nickname=nickname,
        tags=["<tag>", "beta"] if tags is None else tags,
        active=active,
    )


async def render(view: SqlalchemyModelView[Person], model: Person) -> list[str]:
    rows = await view.map_to_json([model], request=grid_request())
    row = rows[0]
    assert isinstance(row, list)
    return row


def column(
    view: SqlalchemyModelView[Person], row: Sequence[str], source_name: str
) -> str:
    names = [field.source_field_name for field in view.fields]
    return row[names.index(source_name)]


@pytest.mark.asyncio
async def test_text_cell_shows_markup_as_text() -> None:
    view = NameView()
    row = await render(view, make_person())

    assert column(view, row, "name") == "&lt;b&gt;x&lt;/b&gt;"


@pytest.mark.asyncio
async def test_email_cell_escapes_quote_in_href() -> None:
    view = EmailView()
    row = await render(view, make_person())

    assert column(view, row, "email") == (
        "<a href='mailto:a&#34;@b.com'>a&#34;@b.com</a>"
    )


@pytest.mark.asyncio
async def test_file_field_keeps_the_next_column() -> None:
    view = FileView()
    row = await render(view, make_person())

    assert len(row) == len(view.fields)
    assert column(view, row, "attachment") == "&lt;script&gt;"
    assert column(view, row, "nickname") == "nick"


@pytest.mark.asyncio
async def test_missing_file_is_a_dash_cell() -> None:
    view = FileView()
    row = await render(view, make_person(attachment=None))

    assert len(row) == len(view.fields)
    assert column(view, row, "attachment") == "-"
    assert column(view, row, "nickname") == "nick"


@pytest.mark.asyncio
async def test_list_cell_escapes_items() -> None:
    view = TagView()
    row = await render(view, make_person())

    assert column(view, row, "tags") == "&lt;tag&gt;, beta"


@pytest.mark.asyncio
async def test_list_from_json_returns_child_values() -> None:
    field = ListField(child_field=TextField(), source_field=Person.tags)
    mapper = field.mapper
    assert mapper is not None

    assert await mapper.from_json(["alpha", "beta"]) == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_boolean_true_cell_uses_json_text() -> None:
    view = ActiveView()
    row = await render(view, make_person())

    assert column(view, row, "active") == "✅"
