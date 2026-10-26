import uuid

from phoenix_admin.ext.sqla.pk import Pk
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ByName(Base):
    __tablename__ = "by_name"

    id: Mapped[int] = mapped_column(primary_key=True)


class ByAttribute(Base):
    __tablename__ = "by_attribute"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)


class Composite(Base):
    __tablename__ = "composite"

    a: Mapped[int] = mapped_column(primary_key=True)
    b: Mapped[uuid.UUID] = mapped_column(primary_key=True)


def test_string_pk_extracts_scalar() -> None:
    row = ByName(id=5)

    assert Pk("id").extract_value(row) == "5"


def test_attribute_pk_stringifies_uuid() -> None:
    value = uuid.uuid4()
    row = ByAttribute(id=value)

    assert Pk(ByAttribute.id).extract_value(row) == str(value)


def test_composite_pk_stringifies_each_part() -> None:
    value = uuid.uuid4()
    row = Composite(a=1, b=value)

    assert Pk((Composite.a, Composite.b)).extract_value(row) == f"1,{value}"


def test_columns_resolve_name_and_attributes() -> None:
    assert Pk("id").columns(ByName) == (ByName.id,)
    assert Pk(ByAttribute.id).columns(ByAttribute) == (ByAttribute.id,)
    assert Pk((Composite.a, Composite.b)).columns(Composite) == (
        Composite.a,
        Composite.b,
    )
    assert Pk([Composite.a, Composite.b]).columns(Composite) == (
        Composite.a,
        Composite.b,
    )
