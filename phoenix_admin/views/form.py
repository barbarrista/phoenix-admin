from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from typing import Generic, TypeVar, get_args, get_type_hints

from pydantic import BaseModel
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from phoenix_admin.fields.base import BaseField
from phoenix_admin.responses import AsJsonResponse
from phoenix_admin.utils import getval, qualname
from phoenix_admin.views.base import View

_T = TypeVar("_T", bound=BaseModel | None)


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestContext(Generic[_T]):
    request: Request
    templates: Jinja2Templates
    _form_data: _T | None = None

    @property
    def form_data(self) -> _T:
        return getval(self._form_data)


def _collect_fields(cls: type[_T]) -> list[BaseField]:
    fields: list[BaseField] = []
    for field_name, annotation in get_type_hints(cls, include_extras=True).items():
        for form_field in get_args(annotation):
            if not isinstance(form_field, BaseField):
                continue

            form_field.name = field_name
            fields.append(form_field)
            break

    return fields


class BaseFormView(View, Generic[_T]):
    __form_model__: type[_T]

    template = "form.html"
    form_fields: Sequence[BaseField]

    def __init_subclass__(cls) -> None:
        if cls.__form_model__ is None:
            cls.form_fields = []  # type: ignore[unreachable]
        elif issubclass(cls.__form_model__, BaseModel):
            cls.form_fields = _collect_fields(cls.__form_model__)

    def __class_getitem__(cls, item: type[_T]) -> "BaseFormView[_T]":
        cls_name = "BaseFormView[None]"
        if item is not None:
            cls_name = f"BaseFormView[{qualname(item)}]"

        return type(
            cls_name,
            (cls,),
            {"__form_model__": item},
        )  # type: ignore[return-value]

    async def handle(self, request: Request, templates: Jinja2Templates) -> Response:
        template = templates.get_template(self.template)

        match request.method:
            case "GET":
                result = await self.get(
                    ctx=RequestContext(
                        templates=templates,
                        request=request,
                    ),
                )

            case "POST":
                form_data = None
                cls = self.__form_model__
                if cls is not None:
                    form_data = cls.model_validate(await request.form())  # type:ignore[attr-defined]

                result = await self.post(
                    ctx=RequestContext(
                        templates=templates,
                        request=request,
                        _form_data=form_data,  # type:ignore[arg-type]
                    ),
                )

            case _ as unexpected:
                msg = f"Got unexpected method: {unexpected}"
                raise ValueError(msg)

        if isinstance(result, Response):
            return result

        json_result = None
        result_data = None
        if isinstance(result, AsJsonResponse):
            json_result = result.dump()
            result_data = None

        if isinstance(result, BaseModel):
            result_data = result.model_dump(mode="json")

        rendered_template = template.render(
            request=request,
            view=self,
            result=result_data,
            json_result=json_result,
            form_fields=await self.get_form_fields(),
        )

        return Response(
            status_code=HTTPStatus.OK,
            content=rendered_template,
            headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
        )

    async def _get_default_response(self, ctx: RequestContext[_T]) -> Response:
        template = ctx.templates.get_template(self.template)
        rendered_template = template.render(
            request=ctx.request,
            view=self,
            form_fields=await self.get_form_fields(),
            result_fields=None,
        )
        return Response(
            status_code=HTTPStatus.OK,
            content=rendered_template,
            headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
        )

    async def get(
        self,
        ctx: RequestContext[_T],
    ) -> Response | BaseModel | AsJsonResponse:
        return await self._get_default_response(ctx)

    async def post(
        self,
        ctx: RequestContext[_T],
    ) -> Response | BaseModel | AsJsonResponse:
        return await self._get_default_response(ctx)

    async def get_form_fields(self) -> Sequence[BaseField]:
        return self.form_fields
