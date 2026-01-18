from typing import TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel | None)
