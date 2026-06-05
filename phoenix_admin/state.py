from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.requests import Request

if TYPE_CHECKING:
    from phoenix_admin.admin import AdminApp
    from phoenix_admin.ext.sqla.view import SqlalchemyModelView
    from phoenix_admin.extensions.manager import ExtensionManager


class AppState:
    def __init__(
        self,
        state: State,
        *,
        admin_app: "AdminApp",
        admin_route_name: str,
        extension_manager: "ExtensionManager",
        model_view_registry: Mapping[str, "SqlalchemyModelView[Any]"],
    ) -> None:
        self._state = state

        for key, value in (
            ("admin_app", admin_app),
            ("asgi_app", admin_app.asgi_app),
            ("admin_route_name", admin_route_name),
            ("extension_manager", extension_manager),
            ("model_view_registry", model_view_registry),
        ):
            if key not in self._state._state:  # noqa: SLF001
                setattr(self._state, key, value)

    @property
    def admin_route_name(self) -> str:
        return cast("str", self._state.admin_route_name)

    @property
    def asgi_app(self) -> Starlette:
        return cast("Starlette", self._state.asgi_app)

    @property
    def admin_app(self) -> "AdminApp":
        return cast("AdminApp", self._state.admin_app)

    @property
    def extension_manager(self) -> "ExtensionManager":
        return cast("ExtensionManager", self._state.extension_manager)

    @property
    def model_view_registry(self) -> Mapping[str, "SqlalchemyModelView[Any]"]:
        return cast(
            "Mapping[str, SqlalchemyModelView[Any]]",
            self._state.model_view_registry,
        )


def get_app_state(request: Request) -> AppState:
    """Returns typed structure `AppState` from request (Starlette.state field)"""

    return cast("AppState", request.app.state.app_state)
