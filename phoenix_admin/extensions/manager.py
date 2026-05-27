from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager

from starlette.requests import Request

from phoenix_admin.extensions.extension import OnRequestExtension


class ExtensionManager:
    def __init__(self, extensions: list[OnRequestExtension] | None = None) -> None:
        self._extensions = extensions or []

    def add_extension(self, extension: OnRequestExtension) -> None:
        self._extensions.append(extension)

    @property
    def extensions(self) -> Sequence[OnRequestExtension]:
        return self._extensions

    @asynccontextmanager
    async def on_request(self, request: Request) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            for ext in self._extensions:
                await stack.enter_async_context(ext.on_request(request))

            yield
