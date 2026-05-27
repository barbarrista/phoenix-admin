from contextlib import AbstractAsyncContextManager
from typing import Protocol

from starlette.requests import Request


class OnRequestExtension(Protocol):
    def on_request(
        self,
        request: Request,
    ) -> AbstractAsyncContextManager[None]: ...
