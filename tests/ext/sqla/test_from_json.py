import pytest
from phoenix_admin.ext.sqla.fields import RelationshipField
from phoenix_admin.ext.sqla.mapper import SqlalchemyMapper
from phoenix_admin.fields.fields import FileField, TextField
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Subdivision(Base):
    __tablename__ = "subdivision"

    id: Mapped[int] = mapped_column(primary_key=True)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str] = mapped_column()
    subdivision_id: Mapped[int | None] = mapped_column(ForeignKey("subdivision.id"))
    subdivision: Mapped[Subdivision | None] = relationship()


@pytest.mark.asyncio
async def test_from_json_keys_result_by_source_field_name() -> None:
    field = TextField(source_field=User.first_name)

    result = await SqlalchemyMapper().from_json({"first_name": "Ann"}, [field])

    assert result == {"first_name": "Ann"}


@pytest.mark.asyncio
async def test_from_json_reads_field_name_when_it_is_set() -> None:
    field = TextField(source_field=User.first_name)
    field.name = "given_name"

    result = await SqlalchemyMapper().from_json(
        {"given_name": "Ann", "first_name": "Bea"},
        [field],
    )

    assert result == {"first_name": "Ann"}


@pytest.mark.asyncio
async def test_from_json_skips_field_without_mapper() -> None:
    file_field = FileField(source_field=User.first_name)
    text_field = TextField(source_field=User.last_name)

    result = await SqlalchemyMapper().from_json(
        {"first_name": "file", "last_name": "Ann"},
        [file_field, text_field],
    )

    assert result == {"last_name": "Ann"}


@pytest.mark.asyncio
async def test_from_json_requires_source_field() -> None:
    field = TextField()

    with pytest.raises(ValueError, match="source_field"):
        await SqlalchemyMapper().from_json({"first_name": "Ann"}, [field])


@pytest.mark.asyncio
async def test_relationship_from_json_is_not_implemented() -> None:
    field = RelationshipField(identity="subdivision", source_field=User.subdivision)

    with pytest.raises(NotImplementedError):
        await SqlalchemyMapper().from_json({"subdivision": "1"}, [field])
