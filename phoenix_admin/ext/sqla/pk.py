from collections.abc import Sequence
from typing import Any, Final, TypeAlias

from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

PkFields: TypeAlias = (
    list[str]
    | tuple[str, ...]
    | Sequence[InstrumentedAttribute[Any]]
    | str
    | InstrumentedAttribute[Any]
)


class Pk:
    def __init__(self, pk: PkFields) -> None:
        self.pk: Final = pk

    def extract_value(self, model: DeclarativeBase) -> str:
        if isinstance(self.pk, list | Sequence | tuple):
            keys = tuple(
                item if isinstance(item, str) else item.key for item in self.pk
            )
            return ",".join(getattr(model, key) for key in keys)

        if isinstance(self.pk, InstrumentedAttribute):
            return str(getattr(model, self.pk.key))

        return str(getattr(model, self.pk))
