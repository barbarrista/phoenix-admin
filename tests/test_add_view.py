from typing import cast

import pytest
from phoenix_admin.admin import AdminApp
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from phoenix_admin.fields.fields import TextField
from phoenix_admin.state import AppState
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


class NamedView(SqlalchemyModelView[User]):
    pk_field = Pk(User.id)
    __config__ = ModelViewConfig()
    fields = (TextField(source_field=User.name),)


class UserView(NamedView):
    identity = "user"


class DuplicateUserView(NamedView):
    identity = "user"


class EmptyFieldsView(SqlalchemyModelView[User]):
    identity = "empty"
    pk_field = Pk(User.id)
    __config__ = ModelViewConfig()
    fields = ()


class MissingFieldsView(SqlalchemyModelView[User]):
    identity = "missing"
    pk_field = Pk(User.id)
    __config__ = ModelViewConfig()


@pytest.fixture
def admin() -> AdminApp:
    return AdminApp()


def registry(admin: AdminApp) -> dict[str, SqlalchemyModelView[User]]:
    state = cast("AppState", admin.asgi_app.state.app_state)
    return cast("dict[str, SqlalchemyModelView[User]]", state.model_view_registry)


def test_add_view_registers_a_model_view(admin: AdminApp) -> None:
    view = UserView()

    admin.add_view(view)

    assert registry(admin)["user"] is view


def test_missing_fields_are_rejected(admin: AdminApp) -> None:
    with pytest.raises(ValueError, match="fields"):
        admin.add_view(MissingFieldsView())

    assert "missing" not in registry(admin)


def test_empty_fields_are_rejected(admin: AdminApp) -> None:
    with pytest.raises(ValueError, match="fields"):
        admin.add_view(EmptyFieldsView())

    assert "empty" not in registry(admin)


def test_duplicate_identity_is_rejected(admin: AdminApp) -> None:
    first = UserView()
    admin.add_view(first)

    with pytest.raises(ValueError, match='Identity "user" is already registered'):
        admin.add_view(DuplicateUserView())

    assert registry(admin)["user"] is first
