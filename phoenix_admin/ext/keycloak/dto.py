from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TokenCookieNames:
    access: str
    refresh: str


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
