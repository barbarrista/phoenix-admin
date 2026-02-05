from http import HTTPStatus
from typing import TYPE_CHECKING, TypeAlias
from urllib.parse import urlencode

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Match, Mount, Route, WebSocketRoute
from starlette.types import ASGIApp

from phoenix_admin.auth.dto import AdminUser
from phoenix_admin.constants import INDEX_ROUTE_NAME, USER_SCOPE_KEY
from phoenix_admin.state import get_app_state

if TYPE_CHECKING:
    from phoenix_admin.auth.provider import BaseAuthProvider

_RouteCompatible: TypeAlias = Mount | Route | WebSocketRoute


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        provider: "BaseAuthProvider",
        dispatch: DispatchFunction | None = None,
    ) -> None:
        super().__init__(app, dispatch)

        self._provider = provider

    async def dispatch(  # noqa: C901
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        state = get_app_state(request)

        target_route: _RouteCompatible | None = None
        for route in state.asgi_app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and isinstance(route, _RouteCompatible):
                target_route = route
                break

        url = request.url_for(
            f"{state.admin_route_name}:{self._provider.sign_in_route_name}"
        )
        params = urlencode({"next": str(request.url)})
        default_response = RedirectResponse(
            f"{url}?{params}",
            status_code=HTTPStatus.SEE_OTHER,
        )

        if target_route is None:
            return await call_next(request)

        if target_route.name in self._provider.not_login_required_routes:
            if target_route.name == self._provider.sign_in_route_name:
                auth_result = await self._provider.authenticate(request)
                if auth_result.is_authenticated:
                    request = _set_user_to_scope(
                        request,
                        user=auth_result.authenticated_user,
                    )
                    return RedirectResponse(
                        request.url_for(
                            state.admin_route_name + f":{INDEX_ROUTE_NAME}"
                        ),
                        status_code=HTTPStatus.SEE_OTHER,
                    )

            return await call_next(request)

        auth_result = await self._provider.authenticate(request)
        if auth_result.is_authenticated:
            request = _set_user_to_scope(request, user=auth_result.authenticated_user)
            return await call_next(request)

        return default_response


def _set_user_to_scope(request: Request, *, user: AdminUser) -> Request:
    request.scope[USER_SCOPE_KEY] = user
    return request
