from dataclasses import dataclass

from pydantic import BaseModel, SecretStr

from phoenix_admin.utils import getval


@dataclass(frozen=True, slots=True, kw_only=True)
class AdminUser:
    username: str = "Admin"
    avatar_url: str | None = None
    info: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthenticationResult:
    is_authenticated: bool
    user: AdminUser | None = None

    @property
    def authenticated_user(self) -> AdminUser:
        return getval(self.user)


class AuthData(BaseModel):
    username: str
    password: SecretStr
