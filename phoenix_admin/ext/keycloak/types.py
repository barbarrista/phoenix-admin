from typing import Any, TypeAlias, TypeVar

TToken_co = TypeVar("TToken_co", covariant=True)
RawAccessTokenType: TypeAlias = dict[Any, Any]
