from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from phoenix_admin.state import get_app_state


class ExtensionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        state = get_app_state(request)
        async with state.extension_manager.on_request(request):
            return await call_next(request)
