from dataclasses import dataclass
from typing import Any

import pydantic


class PaginationResponseSchema(pydantic.BaseModel):
    results: list[list[Any]]
    count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PaginationParamsDTO:
    limit: int | None = None
    offset: int | None = None
