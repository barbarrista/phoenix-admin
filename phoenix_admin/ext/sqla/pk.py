from typing import Any, Final, TypeAlias, cast

from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

PkComponent: TypeAlias = str | InstrumentedAttribute[Any]
PkFields: TypeAlias = PkComponent | list[PkComponent] | tuple[PkComponent, ...]


class Pk:
    __slots__ = ("pk",)

    def __init__(self, pk: PkFields) -> None:
        self.pk: Final = pk

    def columns(
        self,
        model: type[DeclarativeBase],
    ) -> tuple[InstrumentedAttribute[Any], ...]:
        return tuple(self._column(model, component) for component in self._components())

    def extract_value(self, model: DeclarativeBase) -> str:
        return ",".join(
            str(self._value(model, component)) for component in self._components()
        )

    def _components(self) -> tuple[PkComponent, ...]:
        pk = self.pk
        if isinstance(pk, str):
            return (pk,)

        if isinstance(pk, InstrumentedAttribute):
            return (pk,)

        return tuple(pk)

    def _column(
        self,
        model: type[DeclarativeBase],
        component: PkComponent,
    ) -> InstrumentedAttribute[Any]:
        if isinstance(component, str):
            return cast("InstrumentedAttribute[Any]", getattr(model, component))

        return component

    def _value(self, model: DeclarativeBase, component: PkComponent) -> object:
        attr_name = component if isinstance(component, str) else component.key
        value: object = getattr(model, attr_name)
        return value
