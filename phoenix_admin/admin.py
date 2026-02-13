from collections.abc import Awaitable, Callable
from http import HTTPMethod
from typing import Final

import orjson
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from phoenix_admin.auth.provider import BaseAuthProvider
from phoenix_admin.config import ViewConfig
from phoenix_admin.constants import INDEX_ROUTE_NAME, STATICS_ROUTE_NAME, USER_SCOPE_KEY
from phoenix_admin.exceptions import PhoenixAdminError
from phoenix_admin.fields.base import StructField
from phoenix_admin.protocols import HasMount
from phoenix_admin.state import AppState
from phoenix_admin.views.base import BaseView, View
from phoenix_admin.views.drop_down import DropDown
from phoenix_admin.views.form import BaseFormView
from phoenix_admin.views.index import IndexView
from phoenix_admin.views.link import LinkView


class AdminApp:
    def __init__(  # noqa: PLR0913
        self,
        app: Starlette | None = None,
        *,
        base_url: str = "/admin",
        route_name: str = "admin",
        title: str = "Phoenix Admin",
        index_view: View | None = None,
        debug: bool = False,
        middlewares: list[Middleware] | None = None,
        auth_provider: BaseAuthProvider | None = None,
    ) -> None:
        self._asgi_app: Final = app or Starlette(debug=debug)
        self._views: list[BaseView] = []
        self._view_paths: list[str] = []
        self._title: Final = title

        self.middlewares = middlewares or []
        self.base_url: Final = base_url
        self.route_name: Final = route_name

        self._setup_jinja()
        self._create_index_view(index_view)
        self._init_static_routes()

        self._set_up_asgi_app()
        self._set_up_auth(auth_provider)

        # ↓ Always call this at the end of the method once ↓
        self._extend_asgi_app_middlewares()

    def _extend_asgi_app_middlewares(self) -> None:
        self._asgi_app.user_middleware.extend(self.middlewares)

    def _set_up_asgi_app(self) -> None:
        self.asgi_app.state.app_state = AppState(
            self.asgi_app.state,
            admin_app=self,
            admin_route_name=self.route_name,
        )

    def _set_up_auth(
        self,
        auth_provider: BaseAuthProvider | None = None,
    ) -> None:
        if auth_provider is None:
            return

        self._auth_provider = auth_provider
        self._auth_provider.add_routes_to_app(self)
        middlewares = self._auth_provider.get_depends_middlewares(admin_app=self)
        self.middlewares.extend(middlewares)

    @property
    def asgi_app(self) -> Starlette:
        return self._asgi_app

    def _init_static_routes(self) -> None:
        statics = StaticFiles(packages=["phoenix_admin"])
        self._asgi_app.mount("/statics", app=statics, name=STATICS_ROUTE_NAME)

    def _setup_jinja(self) -> None:
        jinja_env = Environment(
            loader=ChoiceLoader(
                (
                    FileSystemLoader("templates"),
                    PackageLoader("phoenix_admin", "templates"),
                    PackageLoader("phoenix_admin.ext.keycloak", "templates"),
                )
            ),
            autoescape=True,
        )
        self.templates = Jinja2Templates(env=jinja_env)
        self.templates.env.globals["views"] = self._views
        self.templates.env.globals["__admin_panel_title__"] = self._title
        self.templates.env.globals["__admin_route_name__"] = self.route_name
        self.templates.env.filters["to_json"] = lambda data: orjson.dumps(
            data,
            default=str,
            option=orjson.OPT_INDENT_2,
        ).decode()

        self.templates.env.filters["is_dropdown"] = lambda view: isinstance(
            view, DropDown
        )
        self.templates.env.filters["is_form_view"] = lambda view: isinstance(
            view, BaseFormView
        )
        self.templates.env.filters["is_link_view"] = lambda view: isinstance(
            view, LinkView
        )
        self.templates.env.filters["is_struct_field"] = lambda field: isinstance(
            field, StructField
        )
        self.templates.env.filters["is_user_authenticated"] = (
            lambda request: USER_SCOPE_KEY in request.scope
        )

    def _create_index_view(self, index_view: View | None = None) -> None:
        index_view = index_view or IndexView(
            config=ViewConfig(title=self._title, name=INDEX_ROUTE_NAME, path="/")
        )
        self.add_view(index_view, view_name=INDEX_ROUTE_NAME)

    def add_view(
        self,
        view: View | DropDown | LinkView,
        *,
        can_append_in_list: bool = True,
        view_name: str | None = None,
    ) -> None:
        self._validate_view(view)
        if isinstance(view, DropDown):
            for item in view.views:
                self.add_view(item, can_append_in_list=False)

        if isinstance(view, BaseFormView | View):
            path = view.config.path
            self._asgi_app.add_route(
                path=path,
                route=self._handle_view(view),
                methods=[HTTPMethod.GET, HTTPMethod.POST],
                name=view_name or view.config.name,
            )
        if can_append_in_list:
            self._views.append(view)

    def _handle_view(self, view: View) -> Callable[[Request], Awaitable[Response]]:
        async def wrapper(request: Request) -> Response:
            return await view.handle(request, templates=self.templates)

        return wrapper

    def mount_to(self, app: HasMount) -> None:
        app.mount(path=self.base_url, app=self._asgi_app, name=self.route_name)

    def _validate_view(self, view: View | DropDown | LinkView) -> None:
        if isinstance(view, LinkView):
            return

        if isinstance(view, DropDown):
            has_nested_dropdown = any(isinstance(item, DropDown) for item in view.views)
            if has_nested_dropdown:
                msg = "Nested DropDown doesn't supported"
                raise PhoenixAdminError(msg)
            return

        if view.__config__ is None:
            msg = 'Define the "__config__" parameter in your view.\nThis can be done either through a declarative definition in the class itself or through the config parameter when initializing the view.'
            raise ValueError(msg)

        if (path := view.config.path) in self._view_paths:
            msg = f'Path "{path}" already reserved'
            raise ValueError(msg)

        if not view.template:
            msg = 'Define "template" field in View'
            raise ValueError(msg)
