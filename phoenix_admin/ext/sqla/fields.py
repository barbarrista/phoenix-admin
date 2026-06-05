from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm.strategy_options import _AbstractLoad

from phoenix_admin.ext.sqla.mappers import RelationshipMapper
from phoenix_admin.fields.fields import BaseField, FieldTypes


@dataclass(kw_only=True)
class RelationshipField(BaseField):
    field_type: FieldTypes = field(default="relationship", init=False)
    form_template = "form_fields/select.html"
    identity: str
    load_strategy: Callable[[], _AbstractLoad] | None = None
    mapper: RelationshipMapper = field(default_factory=RelationshipMapper)
