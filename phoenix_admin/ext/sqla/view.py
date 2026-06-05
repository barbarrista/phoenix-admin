from collections.abc import Sequence
from http import HTTPMethod, HTTPStatus
from typing import Annotated, Any, ClassVar, Generic, Literal, TypeAlias, TypeVar

import jinja2
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute
from sqlalchemy.sql.functions import count
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.templating import Jinja2Templates
from typing_extensions import Doc

from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.dto import PaginationParamsDTO
from phoenix_admin.ext.sqla.fields import RelationshipField
from phoenix_admin.ext.sqla.mapper import SqlalchemyMapper
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.utils import (
    get_db_session,
    get_default_load_strategy,
    get_field_name,
)
from phoenix_admin.fields.fields import BaseField
from phoenix_admin.request_action import RequestAction
from phoenix_admin.state import get_app_state
from phoenix_admin.table import TableColumnProps, TableColumnPropsList
from phoenix_admin.utils import cast_int, get_request_action, getval, qualname
from phoenix_admin.views.base import BaseView

PkFields: TypeAlias = (
    list[str]
    | tuple[str, ...]
    | Sequence[InstrumentedAttribute[Any]]
    | str
    | InstrumentedAttribute[Any]
)
_TModel = TypeVar("_TModel", bound=DeclarativeBase)


class SqlalchemyModelView(BaseView, Generic[_TModel]):
    __orm_model__: type[_TModel]
    __config__: ClassVar[ModelViewConfig | None] = None
    __mapper__: ClassVar[SqlalchemyMapper] = SqlalchemyMapper()

    fields: ClassVar[
        Annotated[
            Sequence[BaseField],
            Doc("Fields that will appear on the list, view, and edit page"),
        ]
    ]
    identity: ClassVar[
        Annotated[
            str,
            Doc("The view ID by which the view class can be found"),
        ]
    ]
    pk_field: Annotated[Pk, Doc("Primary key field/fields")]

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

    async def _apply_load_strategies(
        self,
        base_stmt: Select[tuple[_TModel]],
    ) -> Select[tuple[_TModel]]:
        relationship_fields = [
            item for item in self.fields if isinstance(item, RelationshipField)
        ]
        if not relationship_fields:
            return base_stmt

        for field in relationship_fields:
            model_field = getattr(
                self.__orm_model__,
                get_field_name(getval(field.source_field)),
            )

            load_strategy = get_default_load_strategy(model_field)
            if field.load_strategy:
                load_strategy = field.load_strategy()

            base_stmt = base_stmt.options(load_strategy)

        return base_stmt

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
        stmt = await self._apply_load_strategies(base_stmt=stmt)
        total = await self.get_count(stmt, session=session)

        result = await self.get_list(stmt, dto=dto, session=session)
        data = await self.map_to_json(result, request=request)

        return JSONResponse(
            content={
                "results": data,
                "count": total,
            }
        )

    async def map_to_json(
        self,
        data: Sequence[_TModel],
        request: Request,
    ) -> Sequence[Any]:
        state = get_app_state(request)
        mapped_entities = [
            await self.__mapper__.to_json(
                model=item,
                fields=self.fields,
                model_view_registry=state.model_view_registry,
            )
            for item in data
        ]
        return [list((item).values()) for item in mapped_entities]

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
        table_columns = await self._get_table_columns(request)
        rendered_template = template.render(
            request=request,
            view=self,
            title=self.config.title,
            ident=ident,
            table_columns=table_columns.model_dump_json(),
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

    async def _get_table_columns(self, request: Request) -> TableColumnPropsList:  # noqa: ARG002
        return TableColumnPropsList(
            [
                TableColumnProps(
                    id=item.column_props.id or item.name or item.source_field_name,
                    name=(
                        item.column_props.name
                        or item.label
                        or item.name
                        or item.source_field_name
                    ),
                    width=item.column_props.width,
                    sort=item.column_props.sort,
                    hidden=item.column_props.hidden,
                )
                for item in self.fields
            ]
        )

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

    async def repr_model(
        self,
        request: Request | None,  # noqa: ARG002
        model: _TModel,
        request_type: Literal["list", "field_access"],  # noqa: ARG002
    ) -> str:
        return repr(model)
