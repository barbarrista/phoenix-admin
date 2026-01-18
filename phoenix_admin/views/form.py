from collections import defaultdict
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final, Generic, get_args, get_type_hints

from jinja2 import Template
from pydantic import BaseModel, ValidationError
from result import Err
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from phoenix_admin.fields.base import BaseField, FileField
from phoenix_admin.responses import AsJsonResponse
from phoenix_admin.utils import getval, qualname
from phoenix_admin.views.base import View
from phoenix_admin.views.form_validation.pydantic_ import (
    PydanticModelValidator,
    get_form_errors,
)
from phoenix_admin.views.types_ import TModel


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestContext(Generic[TModel]):
    request: Request
    templates: Jinja2Templates
    _form_data: TModel | None = None

    @property
    def form_data(self) -> TModel:
        return getval(self._form_data)


def _collect_fields(cls: type[TModel]) -> list[BaseField]:
    fields: list[BaseField] = []
    for field_name, annotation in get_type_hints(cls, include_extras=True).items():
        for form_field in get_args(annotation):
            if not isinstance(form_field, BaseField):
                continue

            form_field.name = field_name
            fields.append(form_field)
            break

    return fields


class BaseFormView(View, Generic[TModel]):
    __form_model__: type[TModel] | None = None

    template = "form.html"
    form_fields: Sequence[BaseField]
    default_headers: Final = Headers({"Content-Type": "text/html; charset=utf-8"})

    def __init_subclass__(cls) -> None:
        if cls.__form_model__ is None:
            cls.form_fields = []
        elif issubclass(cls.__form_model__, BaseModel):
            cls.form_fields = _collect_fields(cls.__form_model__)

    def __class_getitem__(cls, item: type[TModel]) -> "BaseFormView[TModel]":
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
                cls = self.__form_model__
                form_data = await self._get_form_data(request)
                form_data_result = PydanticModelValidator(cls).validate(form_data)
                if isinstance(form_data_result, Err):
                    result = await self._render_errors(
                        template=template,
                        ctx=RequestContext(templates=templates, request=request),
                        exc=form_data_result.err_value,
                    )
                else:
                    result = await self.post(
                        ctx=RequestContext(
                            templates=templates,
                            request=request,
                            _form_data=form_data_result.ok_value,
                        )
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
            headers=self.default_headers,
        )

    async def _get_form_data(self, request: Request) -> Mapping[str, Any]:
        """Prepares form data for Pydantic validation.

        Extracts form data from the request and removes empty UploadFile objects,
        which are automatically created by the browser for unselected file fields.

        Args:
        request: starlette.requests

        Returns:
        Dictionary of form data. All UploadFile objects are checked for "emptiness":
        - filename is missing (None) OR an empty string
        - size == 0 bytes

        Note:
        The field is considered empty if both conditions are met.
        This prevents the removal of legitimate empty text files,
        which might have size=0 but filename != None.
        """
        raw_data = await request.form()
        file_fields = {
            field.name for field in self.form_fields if isinstance(field, FileField)
        }

        multiple_fields = tuple(item.name for item in self.form_fields if item.multiple)
        form_data: MutableMapping[str, Any] = {
            key: value for key, value in raw_data.items() if key not in multiple_fields
        }

        multiple_data = defaultdict(list)
        for field, value in raw_data.multi_items():
            if field not in multiple_fields:
                continue

            multiple_data[field].append(value)

        form_data.update(multiple_data)

        for file_field in file_fields:
            upload_file = form_data.get(file_field)
            if not isinstance(upload_file, UploadFile):
                continue

            filename = (upload_file.filename or "").strip()
            if not filename and upload_file.size == 0:
                # Exclude empty UploadFile objects
                del form_data[file_field]

        return form_data

    async def _get_default_response(self, ctx: RequestContext[TModel]) -> Response:
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
            headers=self.default_headers,
        )

    async def get(
        self,
        ctx: RequestContext[TModel],
    ) -> Response | BaseModel | AsJsonResponse:
        return await self._get_default_response(ctx)

    async def post(
        self,
        ctx: RequestContext[TModel],
    ) -> Response | BaseModel | AsJsonResponse:
        return await self._get_default_response(ctx)

    async def _render_errors(
        self,
        template: Template,
        ctx: RequestContext[TModel],
        *,
        exc: ValidationError,
    ) -> Response | BaseModel | AsJsonResponse:
        errors = get_form_errors(exc)
        raw_data = await ctx.request.form()
        rendered_template = template.render(
            request=ctx.request,
            view=self,
            form_fields=await self.get_form_fields(raw_data),
            result_fields=None,
            errors=errors,
        )
        return Response(
            status_code=HTTPStatus.BAD_REQUEST,
            content=rendered_template,
            headers=self.default_headers,
        )

    async def get_form_fields(
        self,
        data: Mapping[str, Any] | None = None,
    ) -> Sequence[BaseField]:
        if data is None:
            return self.form_fields

        fields = {field.name: field for field in self.form_fields}
        return [
            fields[field_name].copy(value=value) for field_name, value in data.items()
        ]
