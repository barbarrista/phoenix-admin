from typing import Any, Generic, cast

from pydantic import ValidationError
from result import Ok, Result, as_result

from phoenix_admin.utils import getval
from phoenix_admin.views.types_ import TModel


class PydanticModelValidator(Generic[TModel]):
    def __init__(self, cls: type[TModel] | None = None) -> None:
        self._cls = cls

    def validate(self, value: Any) -> Result[TModel | None, ValidationError]:  # noqa: ANN401
        if self._cls is None:
            return Ok(None)

        return self._validate(value)

    @as_result(ValidationError)
    def _validate(self, value: Any) -> TModel:  # noqa: ANN401
        return cast("TModel", getval(self._cls).model_validate(value))  # type:ignore[attr-defined]


def get_form_errors(exc: ValidationError) -> dict[str, str]:
    """
    Transform ValidationError to dict: {field_name: error_message}
    """
    errors: dict[str, str] = {}
    for err in exc.errors():
        loc = ".".join([str(loc) for loc in err["loc"]])
        errors[loc] = err["msg"]
    return errors
