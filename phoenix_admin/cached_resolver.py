from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import timedelta
from typing import Generic, ParamSpec, TypeVar

from phoenix_admin.utils import utc_now

R = TypeVar("R")
P = ParamSpec("P")

_NOT_SET = object()


class Partial(Generic[R]):
    def __init__(
        self,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __call__(self) -> R:
        return self._func(*self._args, **self._kwargs)


class CachedResolver(Generic[R]):
    def __init__(
        self,
        resolver: Callable[[], Awaitable[R]],
        *,
        lock: AbstractAsyncContextManager[None],
        cache_ttl: timedelta = timedelta(hours=1),
    ) -> None:
        self._resolver = resolver
        self._cache_ttl = cache_ttl
        self._expires_at = utc_now() + self._cache_ttl
        self._lock = lock

        self._value: R = _NOT_SET  # type:ignore[assignment]

    async def __call__(self) -> R:
        now = utc_now()
        if self._value == _NOT_SET or self._expires_at < now:
            async with self._lock:
                if self._value == _NOT_SET or self._expires_at < now:
                    self._value = await self._resolver()
                    self._expires_at = utc_now() + self._cache_ttl

        return self._value
