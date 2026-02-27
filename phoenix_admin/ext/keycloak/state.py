import binascii
import hashlib
import hmac
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Final, Self

import orjson

from phoenix_admin.utils import getval


@dataclass(frozen=True, slots=True, kw_only=True)
class StateDTO:
    csrf_token: str
    timestamp: float
    next_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatedStateDTO:
    state: str
    csrf_token: str


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifyingResult:
    is_valid: bool
    state_dto: StateDTO | None = None

    @property
    def state(self) -> StateDTO:
        return getval(self.state_dto)

    @classmethod
    def unsuccess(cls) -> Self:
        return cls(is_valid=False)


class AuthStateManager:
    def __init__(
        self,
        secret_key: str,
        state_ttl: timedelta = timedelta(minutes=5),
    ) -> None:
        self._secret_key = secret_key.encode()
        self.state_ttl: Final = state_ttl

    def create(self, next_url: str) -> CreatedStateDTO:
        state_dto = StateDTO(
            csrf_token=secrets.token_urlsafe(32),
            timestamp=time.time(),
            next_url=next_url,
        )
        state = urlsafe_b64encode(orjson.dumps(state_dto.to_dict())).decode()
        signature = hmac.new(
            self._secret_key,
            state.encode(),
            hashlib.sha256,
        ).hexdigest()
        return CreatedStateDTO(
            state=f"{state}.{signature}",
            csrf_token=state_dto.csrf_token,
        )

    def verify(self, state: str, csrf_token: str) -> VerifyingResult:
        splitted_state = state.rsplit(".", 1)
        expected_length = 2
        if len(splitted_state) != expected_length:
            return VerifyingResult.unsuccess()

        state_part, signature = splitted_state
        expected_signature = hmac.new(
            self._secret_key,
            state_part.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return VerifyingResult.unsuccess()

        state_dto = self._get_state(state_part)
        if state_dto is None:
            return VerifyingResult.unsuccess()

        if (time.time() - state_dto.timestamp) > self.state_ttl.total_seconds():
            return VerifyingResult.unsuccess()

        if state_dto.csrf_token != csrf_token:
            return VerifyingResult.unsuccess()

        return VerifyingResult(is_valid=True, state_dto=state_dto)

    def _get_state(self, state_part: str) -> StateDTO | None:
        try:
            return StateDTO(**orjson.loads(urlsafe_b64decode(state_part).decode()))
        except (orjson.JSONDecodeError, binascii.Error):
            return None
