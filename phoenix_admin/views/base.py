from http import HTTPStatus
from typing import Annotated

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from typing_extensions import Doc

from phoenix_admin.config import ViewConfig
from phoenix_admin.utils import getval


class BaseView:
    pass


class View(BaseView):
    __config__: ViewConfig | None = None
    template: Annotated[str, Doc("HTML template path")]

    def __init__(
        self,
        config: ViewConfig | None = None,
        template: str | None = None,
    ) -> None:
        if config is not None:
            self.__config__ = config

        if template:
            self.template = template

    @property
    def config(self) -> ViewConfig:
        return getval(self.__config__)

    async def handle(self, request: Request, templates: Jinja2Templates) -> Response:
        template = templates.get_template(self.template)
        rendered_template = template.render(request=request, view=self)
        return Response(
            status_code=HTTPStatus.OK,
            content=rendered_template,
            headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
        )
