from collections.abc import Sequence
from typing import Any, Final

from sqlalchemy.orm import DeclarativeBase

from phoenix_admin.fields.fields import BaseField


class SqlalchemyMapper:
    _source_field_error_msg: Final = (
        "source_field is None, may be you forgot set field?"
    )

    async def to_json(
        self,
        model: DeclarativeBase,
        fields: Sequence[BaseField],
    ) -> dict[str, Any]:
        attribute_msg = "Attribute %s doesn't found from model %s"
        mapping: dict[str, Any] = {}
        for field in fields:
            if field.source_field is None:
                raise ValueError(self._source_field_error_msg)

            key = (
                field.source_field
                if isinstance(field.source_field, str)
                else field.source_field.key
            )
            if not hasattr(model, key):
                raise AttributeError(attribute_msg.format(field.source_field, model))

            if field.mapper is None:
                continue

            value = getattr(model, key)
            mapped_value = field.mapper.to_json(
                value,
                is_optional=field.required is False,
            )
            mapping[key] = mapped_value

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

            if field.source_field is None:
                raise ValueError(self._source_field_error_msg)

            value = raw_data.get(field.name)
            parsed_value = field.mapper.from_json(
                value,
                is_optional=field.required is False,
            )
            mapping[field.source_field] = parsed_value

        return mapping
