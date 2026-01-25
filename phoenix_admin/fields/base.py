from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel

from phoenix_admin.not_set import NOT_SET

FieldTypes: TypeAlias = Literal[
    "text",
    "email",
    "password",
    "number",
    "decimal",
    "select",
    "textarea",
    "checkbox",
    "hidden",
    "file",
    "list",
    "date",
    "datetime",
    "struct",
]


@dataclass(kw_only=True)
class BaseField:
    _name: str = field(init=False, default="")

    field_type: FieldTypes = field(default="text", init=False)
    label: str | None = None
    value: Any | None = None
    required: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    error: str | None = None
    readonly: bool = False
    form_template = "form_fields/input.html"
    grid_item_template = "datagrid/default_item.html"
    multiple: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    def get_name_with_index(self, index: int) -> str:
        return f"{self._name}.{index}"


@dataclass(kw_only=True)
class TextField(BaseField):
    field_type: Literal["text"] = field(default="text", init=False)
    form_template = "form_fields/input.html"


@dataclass(kw_only=True)
class EmailField(BaseField):
    field_type: Literal["email"] = field(default="email", init=False)
    form_template = "form_fields/email.html"


@dataclass(kw_only=True)
class PasswordField(BaseField):
    field_type: Literal["password"] = field(default="password", init=False)
    form_template = "form_fields/password.html"


@dataclass(kw_only=True)
class NumberField(BaseField):
    field_type: Literal["number"] = field(default="number", init=False)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    form_template = "form_fields/number.html"


@dataclass(kw_only=True)
class DecimalField(BaseField):
    field_type: Literal["decimal"] = field(default="decimal", init=False)
    min_value: float | None = None
    max_value: float | None = None
    step: str = "any"
    form_template = "form_fields/number.html"


@dataclass(kw_only=True)
class SelectField(BaseField):
    field_type: Literal["select"] = field(default="select", init=False)
    options: list[dict[str, str]] = field(default_factory=list)
    form_template = "form_fields/select.html"


@dataclass(kw_only=True)
class TextAreaField(BaseField):
    field_type: Literal["textarea"] = field(default="textarea", init=False)
    rows: int | None = None
    cols: int | None = None
    form_template = "form_fields/textarea.html"


@dataclass(kw_only=True)
class CheckboxField(BaseField):
    field_type: Literal["checkbox"] = field(default="checkbox", init=False)
    disabled: bool = False
    form_template = "form_fields/checkbox.html"


@dataclass(kw_only=True)
class HiddenField(BaseField):
    field_type: Literal["hidden"] = field(default="hidden", init=False)
    label: str | None = field(default=None, init=False)
    placeholder: str | None = field(default=None, init=False)
    help_text: str | None = field(default=None, init=False)
    form_template = "form_fields/hidden.html"


@dataclass(kw_only=True)
class FileField(BaseField):
    field_type: Literal["file"] = field(default="file", init=False)
    accept: str | None = None
    multiple: bool = False
    form_template = "form_fields/file.html"


@dataclass(kw_only=True)
class ListField(BaseField):
    child_field: BaseField
    field_type: Literal["list"] = field(default="list", init=False)
    multiple: bool = True
    form_template: str = "form_fields/list.html"
    add_item_btn_title: str = "+ Add item"

    def __post_init__(self) -> None:
        self.child_field.name = self.name

    def get_child_field(self) -> BaseField:
        return self.child_field


@dataclass(kw_only=True)
class DateField(BaseField):
    field_type: Literal["date"] = field(default="date", init=False)
    form_template: str = "form_fields/date.html"


@dataclass(kw_only=True)
class DateTimeField(BaseField):
    field_type: Literal["datetime"] = field(default="datetime", init=False)
    form_template: str = "form_fields/datetime.html"


_TModel = TypeVar("_TModel", bound=BaseModel)


@dataclass(kw_only=True)
class StructField(BaseField, Generic[_TModel]):
    _model: type[_TModel] = field(init=False, repr=False)
    fields: Sequence[BaseField] = field(init=False, repr=False)
    field_type: Literal["struct"] = field(default="struct", init=False)
    form_template: str = "form_fields/struct.html"

    def __post_init__(self) -> None:
        self._model = NOT_SET  # type: ignore[assignment]
        self.fields = []

    @property
    def model(self) -> type[_TModel]:
        if self._model is NOT_SET:
            msg = "_model field doesn't assigned"
            raise TypeError(msg)

        return self._model

    @model.setter
    def model(self, value: type[_TModel]) -> None:
        self._model = value
