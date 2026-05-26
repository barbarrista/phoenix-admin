from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

import jinja2
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from phoenix_admin.request_action import RequestAction
from phoenix_admin.utils import get_request_action, qualname
from phoenix_admin.views.base import BaseView

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

_TModel = TypeVar("_TModel", bound="DeclarativeBase")


class SqlalchemyModelView(BaseView, Generic[_TModel]):
    __orm_model__: type[_TModel]

    identity: ClassVar[str]
    title: str = "ModelView"
    list_template: str = "list.html"
    detail_template: str = "detail.html"
    create_template: str = "create.html"
    update_template: str = "update.html"

    def __class_getitem__(cls, item: type[_TModel]) -> "SqlalchemyModelView[_TModel]":
        cls_name = f"ModelView[{qualname(item)}]"
        return type(
            cls_name,
            (cls,),
            {"__orm_model__": item},
        )  # type: ignore[return-value]

    async def handle(self, request: Request, templates: Jinja2Templates) -> Response:
        action = get_request_action(request)
        template = self._get_template(action, templates=templates)
        match action:
            case RequestAction.list:
                return await self._handle(
                    request=request,
                    template=template,
                )

            case RequestAction.detail:
                return await self._handle(
                    request=request,
                    template=template,
                )

            case RequestAction.create:
                return await self._handle(
                    request=request,
                    template=template,
                )

            case RequestAction.update:
                return await self._handle(
                    request=request,
                    template=template,
                )

            case _ as unexpected:
                msg = f"Got unexpected {qualname(RequestAction)}: {unexpected}"
                raise ValueError(msg)

    async def _handle(
        self,
        request: Request,
        template: jinja2.Template,
    ) -> Response:
        ident = request.path_params.get("ident")
        rendered_template = template.render(
            request=request,
            view=self,
            title=self.title,
            ident=ident,
        )
        if request.method == HTTPMethod.GET:
            return Response(
                status_code=HTTPStatus.OK,
                content=rendered_template,
                headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
            )
        elif request.method == HTTPMethod.POST:  # noqa: RET505
            raise NotImplementedError
        else:
            raise NotImplementedError

    def _get_template(
        self,
        action: RequestAction,
        templates: Jinja2Templates,
    ) -> jinja2.Template:
        match action:
            case RequestAction.list:
                return templates.get_template(self.list_template)

            case RequestAction.detail:
                return templates.get_template(self.detail_template)

            case RequestAction.create:
                return templates.get_template(self.create_template)

            case RequestAction.update:
                return templates.get_template(self.update_template)

            case _ as unexpected:
                msg = f"Got unexpected {qualname(RequestAction)}: {unexpected}"
                raise ValueError(msg)
