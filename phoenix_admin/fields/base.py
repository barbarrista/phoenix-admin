from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass(kw_only=True)
class BaseField:
    _name: str = field(init=False, default="")

    type: str = field(default="text", init=False)
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

    def copy(self, name: str | None = None, value: Any = None) -> "BaseField":  # noqa: ANN401
        """Copy field with new value"""

        data = {
            dataclass_field.name: getattr(self, dataclass_field.name)
            for dataclass_field in fields(self)
        }
        del data["_name"]
        del data["type"]

        instance = self.__class__(**data)
        instance.name = name or self.name

        if not isinstance(self, FileField):
            instance.value = value

        return instance

    def get_name_with_index(self, index: int) -> str:
        return f"{self._name}.{index}"


@dataclass(kw_only=True)
class TextField(BaseField):
    type: str = field(default="text", init=False)
    form_template = "form_fields/input.html"


@dataclass(kw_only=True)
class EmailField(BaseField):
    type: str = field(default="email", init=False)
    form_template = "form_fields/email.html"


@dataclass(kw_only=True)
class PasswordField(BaseField):
    type: str = field(default="password", init=False)
    form_template = "form_fields/password.html"


@dataclass(kw_only=True)
class NumberField(BaseField):
    type: str = field(default="number", init=False)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    form_template = "form_fields/number.html"


@dataclass(kw_only=True)
class SelectField(BaseField):
    type: str = field(default="select", init=False)
    options: list[dict[str, str]] = field(default_factory=list)
    form_template = "form_fields/select.html"


@dataclass(kw_only=True)
class TextAreaField(BaseField):
    type: str = field(default="textarea", init=False)
    rows: int | None = None
    cols: int | None = None
    form_template = "form_fields/textarea.html"


@dataclass(kw_only=True)
class CheckboxField(BaseField):
    type: str = field(default="checkbox", init=False)
    disabled: bool = False
    form_template = "form_fields/checkbox.html"


@dataclass(kw_only=True)
class HiddenField(BaseField):
    type: str = field(default="hidden", init=False)
    label: str | None = field(default=None, init=False)
    placeholder: str | None = field(default=None, init=False)
    help_text: str | None = field(default=None, init=False)
    form_template = "form_fields/hidden.html"


@dataclass(kw_only=True)
class FileField(BaseField):
    type: str = field(default="file", init=False)
    accept: str | None = None
    multiple: bool = False
    form_template = "form_fields/file.html"


@dataclass(kw_only=True)
class ListField(BaseField):
    child_field: BaseField
    type: str = field(default="list", init=False)
    multiple: bool = True
    form_template: str = "form_fields/list.html"
    add_item_btn_title: str = "+ Add item"

    def get_child_field(self) -> BaseField:
        return self.child_field.copy(name=self.name)


@dataclass(kw_only=True)
class DateField(BaseField):
    type: str = field(default="date", init=False)
    form_template: str = "form_fields/date.html"


@dataclass(kw_only=True)
class DateTimeField(BaseField):
    type: str = field(default="datetime", init=False)
    form_template: str = "form_fields/datetime.html"
