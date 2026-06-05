from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pydantic


class PaginationResponseSchema(pydantic.BaseModel):
    results: list[tuple[Any, ...]]
    count: int


class ApiResponseSchema(pydantic.BaseModel):
    result: PaginationResponseSchema


@dataclass(frozen=True, slots=True, kw_only=True)
class PaginationParamsDTO:
    limit: int | None = None
    offset: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipMember:
    represented_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MappedEntity:
    pk: str
    dumped_fields: Mapping[str, Any]
