from typing import Any


class PhoenixAdminError(Exception):
    def __init__(self, msg: str) -> None:
        self.message = msg


class FormValidationError(Exception):
    def __init__(self, errors: dict[str, str] | dict[str, list[str]]) -> None:
        self.errors = {
            key: ([value] if not isinstance(value, list) else value)
            for key, value in errors.items()
        }

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        return self.errors.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.errors
