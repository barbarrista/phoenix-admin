import asyncio
from collections.abc import Sequence
from http import HTTPMethod
from typing import TYPE_CHECKING, Final, Generic

from jwcrypto import jwk
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from phoenix_admin.admin import AdminApp
from phoenix_admin.auth.provider import BaseAuthProvider, create_endpoint_handler
from phoenix_admin.cached_resolver import CachedResolver, Partial
from phoenix_admin.ext.keycloak.dto import (
    CallbackUrl,
    KeycloakConfig,
)
from phoenix_admin.ext.keycloak.middleware import RefreshTokenMiddleware
from phoenix_admin.ext.keycloak.types import TToken_co
from phoenix_admin.state import get_app_state
from phoenix_admin.utils import (
    get_first_query_param_item,
    remove_tokens_from_cookies,
    set_tokens_to_cookie,
)

if TYPE_CHECKING:
    from phoenix_admin.admin import AdminApp


try:
    from keycloak import KeycloakOpenID
except ImportError as exc:
    msg = "python-keycloak doesn't installed. Please, install package with `pip install phoenix-admin[keycloak]`"
    raise ImportError(msg) from exc


class KeycloakAuthProvider(BaseAuthProvider, Generic[TToken_co]):
    def __init__(
        self,
        keycloak_openid: KeycloakOpenID,
        config: KeycloakConfig[TToken_co],
        sign_in_path: str = "/sign-in",
        sign_out_path: str = "/sign-out",
    ) -> None:
        super().__init__(sign_in_path=sign_in_path, sign_out_path=sign_out_path)

        self._config: Final = config
        self._keycloak_openid: Final = keycloak_openid
        self._auth_callback_path: Final = "/auth/callback"
        self.auth_callback_route_name: Final = "auth_callback"

        self._auth_failed_url_path: Final = "/auth/failed"
        self.auth_failed_route_name: Final = "auth_failed"

        self._unauthorized_page_url_path: Final = "/auth/unauthorized"
        self.unauthorized_route_name: Final = "unauthorized"

        self._public_key_resolver = CachedResolver(
            Partial(self._keycloak_openid.a_public_key),
            lock=asyncio.Lock(),
            cache_ttl=self._config.public_key_cache_ttl,
        )

    @property
    def not_login_required_routes(self) -> list[str]:
        items = super().not_login_required_routes
        return [
            self.auth_callback_route_name,
            self.auth_failed_route_name,
            self.unauthorized_route_name,
            *items,
        ]

    @property
    def routes_for_redirect_to_index(self) -> list[str]:
        items = super().routes_for_redirect_to_index
        return [self.unauthorized_route_name, *items]

    async def get_keycloak_public_key(self) -> jwk.JWK:
        public_key = await self._public_key_resolver()
        key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
        return jwk.JWK.from_pem(key.encode("utf-8"))

    async def decode_token(self, raw_access_token: str) -> TToken_co:
        public_key = await self.get_keycloak_public_key()
        access_token = await self._keycloak_openid.a_decode_token(
            raw_access_token,
            key=public_key,
        )
        return self._config.token_parser(access_token)

    def get_depends_middlewares(self, admin_app: "AdminApp") -> Sequence[Middleware]:
        return [
            Middleware(  # This middleware must be above AuthMiddleware.
                RefreshTokenMiddleware,
                cookie_names=self._config.cookie_names,
                keycloak_openid=self._keycloak_openid,
            ),
            *super().get_depends_middlewares(admin_app),
        ]

    async def get_sign_in_response(self, request: Request) -> Response:
        state = get_app_state(request)
        redirect_url = (
            get_first_query_param_item(request, param="next")
            or state.admin_app.base_url
        )
        refresh_token = request.cookies.get(self._config.cookie_names.refresh)
        if refresh_token is not None:
            tokens = await self._keycloak_openid.a_refresh_token(
                refresh_token=refresh_token,
            )
            response = RedirectResponse(redirect_url)
            set_tokens_to_cookie(
                response,
                tokens=tokens,
                token_names=self._config.cookie_names,
                path=state.admin_app.base_url,
            )
            return response

        callback_url = CallbackUrl(
            base_url=str(request.base_url).removesuffix("/"),
            admin_path=state.admin_app.base_url,
            url_path=self._auth_callback_path,
            redirect_url=redirect_url,
        )
        auth_url = await self._keycloak_openid.a_auth_url(
            redirect_uri=callback_url.build(),
            scope=self._config.scope,
        )
        return RedirectResponse(auth_url)

    async def get_auth_callback_response(self, request: Request) -> Response:
        state = get_app_state(request)
        code = get_first_query_param_item(request, param="code")
        if code is None:
            return RedirectResponse(self._auth_failed_url_path)

        redirect_url = get_first_query_param_item(request, param="next")
        if redirect_url is None:
            return RedirectResponse(self._auth_failed_url_path)

        callback_url = CallbackUrl(
            base_url=str(request.base_url).removesuffix("/"),
            admin_path=state.admin_app.base_url,
            url_path=self._auth_callback_path,
            redirect_url=redirect_url,
        )

        raw_tokens = await self._keycloak_openid.a_token(
            code=code,
            redirect_uri=callback_url.build(),
            grant_type=self._config.grant_type,
        )

        response = RedirectResponse(redirect_url)
        set_tokens_to_cookie(
            response,
            tokens=raw_tokens,
            token_names=self._config.cookie_names,
            path=state.admin_app.base_url,
        )
        return response

    async def get_auth_failed_response(self, request: Request) -> Response:  # noqa: ARG002
        return JSONResponse({"code": "auth_error", "message": "Auth failed"})

    async def get_unauthorized_response(self, request: Request) -> Response:
        state = get_app_state(request)
        template_name = "sign_in_from_keycloak.html"
        return state.admin_app.templates.TemplateResponse(  # type: ignore[no-any-return]
            request=request,
            name=template_name,
            context=self._default_context,  # type: ignore[call-overload]
        )

    async def get_sign_out_response(self, request: Request) -> Response:
        state = get_app_state(request)

        refresh_token = request.cookies.pop(self._config.cookie_names.refresh, None)
        if refresh_token:
            await self._keycloak_openid.a_logout(refresh_token)

        response = RedirectResponse(
            request.url_for(f"{state.admin_route_name}:{self.unauthorized_route_name}")
        )
        remove_tokens_from_cookies(
            response,
            token_names=self._config.cookie_names,
            path=state.admin_app.base_url,
        )

        return response

    def add_routes_to_app(self, admin_app: "AdminApp") -> None:
        super().add_routes_to_app(admin_app)

        admin_app.asgi_app.routes.extend(
            (
                Route(
                    self._auth_callback_path,
                    create_endpoint_handler(self.get_auth_callback_response),
                    methods=[HTTPMethod.GET],
                    name=self.auth_callback_route_name,
                ),
                Route(
                    self._auth_failed_url_path,
                    create_endpoint_handler(self.get_auth_failed_response),
                    methods=[HTTPMethod.GET],
                    name=self.auth_failed_route_name,
                ),
                Route(
                    self._unauthorized_page_url_path,
                    create_endpoint_handler(self.get_unauthorized_response),
                    methods=[HTTPMethod.GET, HTTPMethod.POST],
                    name=self.unauthorized_route_name,
                ),
            ),
        )
