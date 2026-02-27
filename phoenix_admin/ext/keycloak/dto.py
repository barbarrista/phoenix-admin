from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Generic

from phoenix_admin.ext.keycloak.types import RawAccessTokenType, TToken_co


@dataclass(frozen=True, slots=True, kw_only=True)
class TokenCookieNames:
    access: str
    refresh: str
    csrf: str

    def __post_init__(self) -> None:
        fields = (self.access, self.refresh, self.csrf)
        if len(set(fields)) != len(fields):
            msg = "All fields (access, refresh, csrf) must be unique"
            raise ValueError(msg)


DEFAULT_TOKEN_COOKIE_NAMES = TokenCookieNames(
    access="admin_access_token",
    refresh="admin_refresh_token",
    csrf="admin_csrf_token",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CallbackUrl:
    base_url: str
    admin_path: str
    url_path: str

    def build(self) -> str:
        return f"{self.base_url}{self.admin_path}{self.url_path}"


@dataclass(frozen=True, slots=True, kw_only=True)
class KeycloakConfig(Generic[TToken_co]):
    token_parser: Callable[[RawAccessTokenType], TToken_co]
    cookie_names: TokenCookieNames = DEFAULT_TOKEN_COOKIE_NAMES
    scope: str = "openid"
    grant_type: str = "authorization_code"
    public_key_cache_ttl: timedelta = timedelta(hours=1)
