from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Final, Literal

from sqlalchemy.orm import DeclarativeBase
from starlette.requests import Request

from phoenix_admin.ext.sqla.fields import RelationshipField
from phoenix_admin.ext.sqla.mappers import RelationshipMapper
from phoenix_admin.ext.sqla.utils import (
    get_field_name,
    is_source_optional,
    why_source_rejects_none,
)
from phoenix_admin.fields.exceptions import UNEXPECTED_NONE_MESSAGE, ParseError
from phoenix_admin.fields.fields import BaseField
from phoenix_admin.utils import qualname

if TYPE_CHECKING:
    from phoenix_admin.ext.sqla.view import SqlalchemyModelView

_MapAction = Literal["serialize", "parse"]


def _field_parse_error(
    exc: ParseError,
    field: BaseField,
    *,
    mapper_name: str,
    action: _MapAction,
    model_name: str | None = None,
) -> ParseError:
    field_name = field.source_field_name or "<unnamed>"
    where = f"field {field_name!r}"
    if model_name is not None:
        where = f"{where} of {model_name}"

    detail = _parse_error_detail(exc, field)
    message = f"Failed to {action} {where} with {mapper_name}"
    if detail:
        message = f"{message}: {detail}"

    return ParseError(message)


def _parse_error_detail(exc: ParseError, field: BaseField) -> str | None:
    detail = exc.message
    if detail == UNEXPECTED_NONE_MESSAGE:
        return (
            why_source_rejects_none(field.source_field, required=field.required)
            or detail
        )

    cause = exc.__cause__
    if not detail and cause is not None:
        return f"{qualname(cause)}: {cause}"

    return detail


class SqlalchemyMapper:
    _source_field_error_msg: Final = (
        "source_field is None, may be you forgot set field?"
    )

    def _require_field_name(self, field: BaseField) -> str:
        source_field = field.source_field
        if source_field is None:
            raise ValueError(self._source_field_error_msg)

        return get_field_name(source_field)

    async def to_json(
        self,
        model: DeclarativeBase,
        fields: Sequence[BaseField],
        model_view_registry: Mapping[str, "SqlalchemyModelView[Any]"],
        request: Request,
    ) -> dict[str, Any]:
        attribute_msg = "Attribute %s doesn't found from model %s"
        mapping: dict[str, Any] = {}
        for field in fields:
            field_name = self._require_field_name(field)
            if not hasattr(model, field_name):
                raise AttributeError(attribute_msg.format(field.source_field, model))

            value = getattr(model, field_name)
            if field.mapper is None:
                mapping[field_name] = value
                continue
            optional = is_source_optional(
                field.source_field,
                required=field.required,
            )
            try:
                if isinstance(field, RelationshipField) and isinstance(
                    field.mapper,
                    RelationshipMapper,
                ):
                    model_view = model_view_registry.get(field.identity)
                    if model_view is None:
                        err_msg = f"For relationship field {field.source_field} model view doesn't found"
                        raise ValueError(err_msg)

                    mapped_value = await field.mapper.to_json(
                        value,
                        is_optional=optional,
                        model_view=model_view,
                        request=request,
                    )
                else:
                    mapped_value = await field.mapper.to_json(
                        value,
                        is_optional=optional,
                        request=request,
                    )
            except ParseError as exc:
                raise _field_parse_error(
                    exc,
                    field,
                    mapper_name=qualname(field.mapper),
                    action="serialize",
                    model_name=type(model).__qualname__,
                ) from exc

            mapping[field_name] = mapped_value

        return mapping

    async def from_json(
        self,
        raw_data: dict[str, Any],
        fields: Sequence[BaseField],
    ) -> dict[str, Any]:
        mapping: dict[str, Any] = {}

        for field in fields:
            if field.mapper is None:
                continue

            source_name = self._require_field_name(field)
            raw_key = field.name or source_name
            try:
                parsed_value = await field.mapper.from_json(
                    raw_data.get(raw_key),
                    is_optional=is_source_optional(
                        field.source_field,
                        required=field.required,
                    ),
                )
            except ParseError as exc:
                raise _field_parse_error(
                    exc,
                    field,
                    mapper_name=type(field.mapper).__name__,
                    action="parse",
                ) from exc

            mapping[source_name] = parsed_value

        return mapping
