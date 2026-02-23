from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Generic

from phoenix_admin.ext.keycloak.types import RawAccessTokenType, TToken_co


@dataclass(frozen=True, slots=True, kw_only=True)
class TokenCookieNames:
    access: str
    refresh: str

    def __post_init__(self) -> None:
        if self.access == self.refresh:
            msg = '"access" field doesn\'t equals "refresh" field'
            raise ValueError(msg)


DEFAULT_TOKEN_COOKIE_NAMES = TokenCookieNames(
    access="access_token",
    refresh="refresh_token",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CallbackUrl:
    base_url: str
    admin_path: str
    url_path: str
    redirect_url: str

    def build(self) -> str:
        return (
            f"{self.base_url}{self.admin_path}{self.url_path}?next={self.redirect_url}"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class KeycloakConfig(Generic[TToken_co]):
    token_parser: Callable[[RawAccessTokenType], TToken_co]
    cookie_names: TokenCookieNames = DEFAULT_TOKEN_COOKIE_NAMES
    scope: str = "openid"
    grant_type: str = "authorization_code"
    public_key_cache_ttl: timedelta = timedelta(hours=1)
