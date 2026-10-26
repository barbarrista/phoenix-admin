from types import SimpleNamespace
from typing import Any, cast

import pytest
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.fields import RelationshipField
from phoenix_admin.ext.sqla.mapper import SqlalchemyMapper
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.utils import why_source_rejects_none
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from phoenix_admin.fields.exceptions import ParseError
from phoenix_admin.fields.fields import FloatField, TextField
from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    DeclarativeBase,
    InstrumentedAttribute,
    Mapped,
    mapped_column,
    relationship,
)
from starlette.requests import Request
from starlette.types import Scope


class Base(DeclarativeBase):
    pass


class Office(Base):
    __tablename__ = "office"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile: Mapped["Profile | None"] = relationship(back_populates="team")


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    team: Mapped[Team] = relationship(back_populates="profile")


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str | None] = mapped_column()
    code: Mapped[str] = mapped_column()
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))
    team: Mapped[Team | None] = relationship()
    office_id: Mapped[int] = mapped_column(ForeignKey("office.id"))
    office: Mapped[Office] = relationship()


class PersonView(SqlalchemyModelView[Person]):
    identity = "person"
    pk_field = Pk(Person.id)
    __config__ = ModelViewConfig(page_limit=10)


class NicknameView(PersonView):
    fields = (TextField(source_field=Person.nickname),)


class RequiredNicknameView(PersonView):
    fields = (TextField(source_field=Person.nickname, required=True),)


class CodeView(PersonView):
    fields = (TextField(source_field=Person.code),)


class TeamView(PersonView):
    fields = (RelationshipField(identity="team", source_field=Person.team),)


class OfficeView(PersonView):
    fields = (RelationshipField(identity="office", source_field=Person.office),)


class ProfileLinkView(SqlalchemyModelView[Team]):
    identity = "team"
    pk_field = Pk(Team.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields = (RelationshipField(identity="profile", source_field=Team.profile),)


class OfficeModelView(SqlalchemyModelView[Office]):
    identity = "office"
    pk_field = Pk(Office.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields = (TextField(source_field=Office.name),)


class ProfileModelView(SqlalchemyModelView[Profile]):
    identity = "profile"
    pk_field = Pk(Profile.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields = (TextField(source_field=Profile.id),)


def grid_request(
    registry: dict[str, SqlalchemyModelView[Any]] | None = None,
) -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "app": SimpleNamespace(
            state=SimpleNamespace(
                app_state=SimpleNamespace(model_view_registry=registry or {}),
            ),
        ),
    }
    return Request(cast("Scope", scope))


def person(**overrides: object) -> Person:
    values: dict[str, object] = {
        "id": 1,
        "nickname": None,
        "code": "ok",
        "team": None,
        "office": None,
    }
    values.update(overrides)
    return Person(**values)


def related_request() -> Request:
    return grid_request(
        {
            "team": ProfileLinkView(),
            "office": OfficeModelView(),
            "profile": ProfileModelView(),
        },
    )


async def first_cell(
    view: SqlalchemyModelView[Person],
    model: Person,
    request: Request | None = None,
) -> str:
    rows = await view.map_to_json([model], request=request or grid_request())
    row = rows[0]
    assert isinstance(row, list)
    cell = row[0]
    assert isinstance(cell, str)
    return cell


@pytest.mark.asyncio
async def test_nullable_column_null_renders_dash() -> None:
    assert await first_cell(NicknameView(), person()) == "-"


@pytest.mark.asyncio
async def test_required_null_on_nullable_column_is_a_parse_error() -> None:
    with pytest.raises(
        ParseError,
        match="the field is declared with required=True, but its value is None",
    ):
        await first_cell(RequiredNicknameView(), person())


@pytest.mark.asyncio
async def test_non_nullable_column_null_is_a_parse_error() -> None:
    with pytest.raises(
        ParseError,
        match="the column is not nullable, but its value is None",
    ):
        await first_cell(CodeView(), person(code=None))


@pytest.mark.asyncio
async def test_nullable_many_to_one_null_renders_dash() -> None:
    assert await first_cell(TeamView(), person(), related_request()) == "-"


@pytest.mark.asyncio
async def test_non_nullable_many_to_one_null_is_a_parse_error() -> None:
    with pytest.raises(
        ParseError,
        match=(
            "Failed to serialize field 'office' of Person with RelationshipMapper: "
            "the foreign key is not nullable, but its value is None"
        ),
    ):
        await first_cell(OfficeView(), person(), related_request())


@pytest.mark.asyncio
async def test_one_to_one_parent_null_is_a_parse_error() -> None:
    view = ProfileLinkView()

    with pytest.raises(
        ParseError,
        match="the relationship is not optional, but its value is None",
    ):
        await view.map_to_json([Team(id=1, profile=None)], request=related_request())


@pytest.mark.asyncio
async def test_string_source_null_is_a_parse_error() -> None:
    field = TextField(source_field="nickname")

    with pytest.raises(
        ParseError,
        match=(
            "Failed to serialize field 'nickname' of Person with TextFieldMapper: "
            "source_field is not a mapped attribute, so None is not accepted"
        ),
    ):
        await SqlalchemyMapper().to_json(
            person(),
            [field],
            {},
            grid_request(),
        )


def test_unknown_mapped_property_rejects_none() -> None:
    class UnknownAttribute(InstrumentedAttribute[object]):
        def __init__(self) -> None:
            self.property = object()

    reason = why_source_rejects_none(UnknownAttribute(), required=False)

    assert reason == "the field does not accept None"


@pytest.mark.asyncio
async def test_from_json_nullable_null_is_none() -> None:
    field = TextField(source_field=Person.nickname)

    result = await SqlalchemyMapper().from_json({"nickname": None}, [field])

    assert result == {"nickname": None}


@pytest.mark.asyncio
async def test_from_json_required_null_is_a_parse_error() -> None:
    field = TextField(source_field=Person.nickname, required=True)

    with pytest.raises(
        ParseError,
        match=(
            "Failed to parse field 'nickname' with TextFieldMapper: "
            "the field is declared with required=True, but its value is None"
        ),
    ):
        await SqlalchemyMapper().from_json({"nickname": None}, [field])


@pytest.mark.asyncio
async def test_from_json_non_nullable_null_is_a_parse_error() -> None:
    field = TextField(source_field=Person.code)

    with pytest.raises(
        ParseError,
        match="the column is not nullable, but its value is None",
    ):
        await SqlalchemyMapper().from_json({"code": None}, [field])


@pytest.mark.asyncio
async def test_from_json_invalid_value_names_the_field_and_cause() -> None:
    field = FloatField(source_field="amount")

    with pytest.raises(
        ParseError,
        match=(
            "Failed to parse field 'amount' with FloatFieldMapper: "
            "ValueError: could not convert string to float: 'nope'"
        ),
    ):
        await SqlalchemyMapper().from_json({"amount": "nope"}, [field])
