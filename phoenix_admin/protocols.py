from typing import Protocol

from starlette.types import ASGIApp


class HasMount(Protocol):
    def mount(self, path: str, app: ASGIApp, name: str | None = None) -> None: ...
