from collections.abc import Awaitable, Callable
from http import HTTPMethod

import orjson
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from phoenix_admin.config import ViewConfig
from phoenix_admin.exceptions import PhoenixAdminError
from phoenix_admin.jinja_helpers import raise_exception
from phoenix_admin.protocols import HasMount
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
        title: str = "Admin Panel",
        index_view: View | None = None,
        debug: bool = False,
    ) -> None:
        self._asgi_app = app or Starlette(debug=debug)
        self._views: list[BaseView] = []
        self._view_paths: list[str] = []
        self._title = title

        self.base_url = base_url
        self.route_name = route_name

        self._setup_jinja()
        self._create_index_view(index_view)
        self._init_static_routes()

    @property
    def asgi_app(self) -> Starlette:
        return self._asgi_app

    def _init_static_routes(self) -> None:
        statics = StaticFiles(packages=["phoenix_admin"])
        self._asgi_app.mount("/statics", app=statics, name="statics")

    def _setup_jinja(self) -> None:
        jinja_env = Environment(
            loader=ChoiceLoader(
                (
                    FileSystemLoader("templates"),
                    PackageLoader("phoenix_admin", "templates"),
                )
            ),
            autoescape=True,
        )
        self.templates = Jinja2Templates(env=jinja_env)
        self.templates.env.globals["views"] = self._views
        self.templates.env.globals["__name__"] = self.route_name
        self.templates.env.globals["raise"] = raise_exception
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

    def _create_index_view(self, index_view: View | None = None) -> None:
        index_view = index_view or IndexView(
            config=ViewConfig(title=self._title, name="index", path="/")
        )
        self.add_view(index_view)

    def add_view(
        self,
        view: View | DropDown | LinkView,
        *,
        can_append_in_list: bool = True,
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
                name=view.config.name,
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
