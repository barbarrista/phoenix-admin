import asyncio
import uuid
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID

import uvicorn
from keycloak import KeycloakOpenID
from phoenix_admin.admin import AdminApp
from phoenix_admin.auth.dto import AdminUser, AuthenticationResult
from phoenix_admin.config import ViewConfig
from phoenix_admin.ext.keycloak.dto import KeycloakConfig
from phoenix_admin.ext.keycloak.provider import KeycloakAuthProvider
from phoenix_admin.ext.keycloak.state import AuthStateManager
from phoenix_admin.fields.base import PasswordField, TextField
from phoenix_admin.utils import get_tokens_from_request
from phoenix_admin.views.form import BaseFormView, RequestContext
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request


class RegistrationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    phone_number: Annotated[str, Field(), TextField(label="Phone Number")]
    password: Annotated[SecretStr, PasswordField(label="Password")]


class UserInfo(BaseModel):
    user_id: UUID
    phone_number: str
    created_by: str


class RegisterView(BaseFormView[RegistrationData]):
    __config__ = ViewConfig(
        name="register",
        title="Registration",
        path="/register",
    )

    async def post(self, ctx: RequestContext[RegistrationData]) -> BaseModel:
        request_user: SuperAdmin = ctx.request.user
        return UserInfo(
            user_id=uuid.uuid4(),
            phone_number=ctx.form_data.phone_number,
            created_by=request_user.username,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthUser:
    id: int
    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SuperAdmin(AdminUser):
    is_superuser: Literal[True] = True
    permissions: list[str]


class DecodedAccessToken(BaseModel):
    sub: UUID
    name: str


JSON_STATHAM_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTjoZ4FsLBNb1fSk7nPqBX6MAcJRKL10O1uoAFtegwAxK1m8eWmEzVAoJyR2b2skk-vU0OKcxxEv6qLlFfngsgJH0H9IKO2-84lwfHV3w&s=10"


class KcAuthProvider(KeycloakAuthProvider[DecodedAccessToken]):
    async def authenticate(self, request: Request) -> AuthenticationResult:
        raw_access_token = get_tokens_from_request(
            request,
            token_name=self._config.cookie_names.access,
        )
        if raw_access_token:
            parsed_token = await self.decode_token(raw_access_token)
            return AuthenticationResult(
                is_authenticated=True,
                user=SuperAdmin(
                    username=parsed_token.name,
                    permissions=["can_view_something", "can_delete_something"],
                    avatar_url=JSON_STATHAM_URL,
                ),
            )

        return AuthenticationResult(is_authenticated=False)


def create_admin_app() -> AdminApp:
    keycloak_openid = KeycloakOpenID(
        server_url="https://sso.yourdomain.com",
        realm_name="your_realm",
        client_id="your_client_id",
    )
    config = KeycloakConfig[DecodedAccessToken](
        token_parser=DecodedAccessToken.model_validate,
    )
    key = "secret"
    admin = AdminApp(
        auth_provider=KcAuthProvider(
            keycloak_openid=keycloak_openid,
            config=config,
            auth_state_manager=AuthStateManager(secret_key=key),
        ),
        middlewares=[Middleware(SessionMiddleware, secret_key=key)],
    )
    admin.add_view(RegisterView())

    return admin


def create_app() -> Starlette:
    main_app = Starlette()
    admin = create_admin_app()
    admin.mount_to(main_app)
    return main_app


async def main() -> None:
    config = uvicorn.Config("examples.keycloak_auth.main:create_app", factory=True)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
