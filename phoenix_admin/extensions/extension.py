from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable

from starlette.requests import Request


class BaseExtension(Protocol): ...


@runtime_checkable
class OnRequestExtension(Protocol):
    def on_request(
        self,
        request: Request,
    ) -> AbstractAsyncContextManager[None]: ...
