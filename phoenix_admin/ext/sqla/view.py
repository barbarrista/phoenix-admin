from collections.abc import Sequence
from http import HTTPMethod, HTTPStatus
from typing import Annotated, Any, ClassVar, Generic, TypeVar

import jinja2
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.functions import count
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.templating import Jinja2Templates
from typing_extensions import Doc

from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.dto import PaginationParamsDTO
from phoenix_admin.ext.sqla.mapper import SqlalchemyMapper
from phoenix_admin.ext.sqla.utils import get_db_session
from phoenix_admin.fields.fields import BaseField
from phoenix_admin.request_action import RequestAction
from phoenix_admin.utils import cast_int, get_request_action, getval, qualname
from phoenix_admin.views.base import BaseView

_TModel = TypeVar("_TModel", bound=DeclarativeBase)


class SqlalchemyModelView(BaseView, Generic[_TModel]):
    __orm_model__: type[_TModel]
    __config__: ClassVar[ModelViewConfig | None] = None
    __mapper__: ClassVar[SqlalchemyMapper] = SqlalchemyMapper()

    fields: Sequence[BaseField]
    identity: ClassVar[str]

    list_template: Annotated[
        str,
        Doc("HTML template path for list page"),
    ] = "list.html"
    detail_template: Annotated[
        str,
        Doc("HTML template path for detail page"),
    ] = "detail.html"
    create_template: Annotated[
        str,
        Doc("HTML template path for create page"),
    ] = "create.html"
    update_template: Annotated[
        str,
        Doc("HTML template path for update page"),
    ] = "update.html"

    @property
    def config(self) -> ModelViewConfig:
        return getval(self.__config__)

    def __class_getitem__(cls, item: type[_TModel]) -> "SqlalchemyModelView[_TModel]":
        cls_name = f"ModelView[{qualname(item)}]"
        return type(
            cls_name,
            (cls,),
            {"__orm_model__": item},
        )  # type: ignore[return-value]

    async def get_list(
        self,
        base_stmt: Select[tuple[_TModel]],
        *,
        session: AsyncSession,
        dto: PaginationParamsDTO,
    ) -> Sequence[_TModel]:
        base_stmt = await self._apply_pagination(base_stmt, dto=dto)
        return (await session.scalars(base_stmt)).all()

    async def get_count(
        self,
        stmt: Select[tuple[_TModel]],
        session: AsyncSession,
    ) -> int:
        count_stmt = select(count()).select_from(stmt.subquery())
        return await session.scalar(count_stmt) or 0

    async def get_list_stmt(self) -> Select[tuple[_TModel]]:
        return select(self.__orm_model__)

    async def _apply_pagination(
        self,
        base_stmt: Select[tuple[_TModel]],
        *,
        dto: PaginationParamsDTO,
    ) -> Select[tuple[_TModel]]:
        limit = dto.limit or self.config.page_limit
        offset = dto.offset or 0
        return base_stmt.limit(limit).offset(offset)

    async def handle_api_request(self, request: Request) -> JSONResponse:
        limit = request.query_params.get("limit")
        offset = request.query_params.get("offset")
        dto = PaginationParamsDTO(limit=cast_int(limit), offset=cast_int(offset))
        session = get_db_session(request)

        stmt = await self.get_list_stmt()
        total = await self.get_count(stmt, session=session)

        result = await self.get_list(stmt, dto=dto, session=session)
        data = await self.map_to_json(result)

        return JSONResponse(
            content={
                "results": data,
                "count": total,
            }
        )

    async def map_to_json(self, data: Sequence[_TModel]) -> Sequence[Any]:
        return [
            list(
                (await self.__mapper__.to_json(model=item, fields=self.fields)).values()
            )
            for item in data
        ]

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
        table_columns = [item.label for item in self.fields]
        rendered_template = template.render(
            request=request,
            view=self,
            title=self.config.title,
            ident=ident,
            table_columns=table_columns,
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
