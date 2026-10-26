from collections.abc import Sequence
from typing import Any, Unpack

from starlette.requests import Request

from phoenix_admin.fields.mappers import BaseFieldMapper, FieldMapperKwargs


class RelationshipMapper(BaseFieldMapper):
    async def to_json(
        self,
        value: Any,  # noqa: ANN401
        *,
        is_optional: bool = False,
        request: Request,
        **kwargs: Unpack[FieldMapperKwargs],
    ) -> Any:  # noqa: ANN401
        if is_optional and value is None:
            return None

        value = self._getval(value)
        model_view = kwargs["model_view"]
        if isinstance(value, Sequence) and not isinstance(value, str | bytes):
            labels = [
                await model_view.repr_model(
                    request=request,
                    model=item,
                    request_type="field_access",
                )
                for item in value
            ]
            return ", ".join(labels)

        return await model_view.repr_model(
            request=request,
            model=value,
            request_type="field_access",
        )

    async def from_json(
        self,
        value: Any,  # noqa: ANN401
        *,
        is_optional: bool = False,
    ) -> Any:  # noqa: ANN401
        raise NotImplementedError
