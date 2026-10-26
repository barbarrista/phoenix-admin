from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy.orm import DeclarativeBase
from starlette.requests import Request

from phoenix_admin.ext.sqla.fields import RelationshipField
from phoenix_admin.ext.sqla.mappers import RelationshipMapper
from phoenix_admin.fields.fields import BaseField

if TYPE_CHECKING:
    from phoenix_admin.ext.sqla.view import SqlalchemyModelView


class SqlalchemyMapper:
    _source_field_error_msg: Final = (
        "source_field is None, may be you forgot set field?"
    )

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
            if field.source_field is None:
                raise ValueError(self._source_field_error_msg)

            field_name = (
                field.source_field
                if isinstance(field.source_field, str)
                else field.source_field.key
            )
            if not hasattr(model, field_name):
                raise AttributeError(attribute_msg.format(field.source_field, model))

            value = getattr(model, field_name)
            if field.mapper is None:
                mapping[field_name] = value
                continue
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
                    is_optional=field.required is False,  # noqa: FIX002, TD003, TD002 # TODO: switch to check None in model field annotation
                    model_view=model_view,
                    request=request,
                )
            else:
                mapped_value = await field.mapper.to_json(
                    value,
                    is_optional=field.required is False,  # noqa: FIX002, TD003, TD002 # TODO: switch to check None in model field annotation
                    request=request,
                )

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

            source_name = field.source_field_name
            if source_name is None:
                raise ValueError(self._source_field_error_msg)

            raw_key = field.name or source_name
            parsed_value = await field.mapper.from_json(
                raw_data.get(raw_key),
                is_optional=field.required is False,
            )
            mapping[source_name] = parsed_value

        return mapping
