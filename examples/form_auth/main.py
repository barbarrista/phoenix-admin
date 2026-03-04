import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID

import uvicorn
from phoenix_admin.admin import AdminApp
from phoenix_admin.auth.dto import AdminUser, AuthData, AuthenticationResult
from phoenix_admin.auth.exceptions import AuthenticationError
from phoenix_admin.auth.provider import FormAuthProvider
from phoenix_admin.config import ViewConfig
from phoenix_admin.exceptions import FormValidationError
from phoenix_admin.fields.base import PasswordField, TextField
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


class AuthProvider(FormAuthProvider):
    async def sign_in(self, form_data: AuthData, *, request: Request) -> None:
        self._validate(form_data)

        if form_data.username == "not_json_statham":
            request.session.update({"username": form_data.username})
            return

        msg = "Error, try again"
        raise AuthenticationError(msg)

    def _validate(self, form_data: AuthData) -> None:
        errors = defaultdict(list)

        if len(form_data.username) <= 2:  # noqa: PLR2004
            errors["username"].append("Ouch, why are there so few letters?")

        if form_data.password.get_secret_value() == "123":
            errors["password"].append(
                'Oops, a user with username "json_statham" already has that password.'
            )

        if not errors:
            return

        raise FormValidationError(errors)

    async def sign_out(self, request: Request) -> None:
        request.session.clear()

    async def authenticate(self, request: Request) -> AuthenticationResult:
        username: str | None = request.session.get("username", None)
        if username == "not_json_statham":
            return AuthenticationResult(
                is_authenticated=True,
                user=SuperAdmin(
                    username="Not Json Statham",
                    permissions=["can_view_something", "can_delete_something"],
                    avatar_url=JSON_STATHAM_URL,
                ),
            )

        return AuthenticationResult(is_authenticated=False)


def create_admin_app() -> AdminApp:
    key = "secret"
    admin = AdminApp(
        auth_provider=AuthProvider(),
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
    config = uvicorn.Config("examples.form_auth.main:create_app", factory=True)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
