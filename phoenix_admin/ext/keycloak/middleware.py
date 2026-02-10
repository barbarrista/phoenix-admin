from typing import TYPE_CHECKING, Any

from keycloak import KeycloakOpenID
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from _logger import logger
from phoenix_admin.utils import set_tokens_to_cookie, set_tokens_to_state

if TYPE_CHECKING:
    from phoenix_admin.ext.keycloak.dto import TokenCookieNames


class RefreshTokenMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        cookie_names: "TokenCookieNames",
        keycloak_openid: KeycloakOpenID,
        dispatch: DispatchFunction | None = None,
    ) -> None:
        super().__init__(app, dispatch)

        self._cookie_names = cookie_names
        self._keycloak_openid = keycloak_openid

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        raw_token = request.cookies.get(self._cookie_names.access)
        refresh_token = request.cookies.get(self._cookie_names.refresh)

        if raw_token is None and refresh_token is None:
            return await call_next(request)

        if raw_token is None and refresh_token is not None:
            tokens = await self._refresh_token(refresh_token)
            if tokens is None:
                return await call_next(request)

            set_tokens_to_state(request, tokens=tokens, token_names=self._cookie_names)
            response = await call_next(request)
            set_tokens_to_cookie(
                response,
                tokens=tokens,
                token_names=self._cookie_names,
            )
            return response

        return await call_next(request)

    async def _refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        try:
            return await self._keycloak_openid.a_refresh_token(
                refresh_token=refresh_token,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(exc)
