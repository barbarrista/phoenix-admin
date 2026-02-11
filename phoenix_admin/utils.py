from datetime import UTC, datetime, timedelta
from inspect import isclass
from typing import Any, TypeVar, cast
from urllib.parse import parse_qs

from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import Response

from phoenix_admin.ext.keycloak.dto import TokenCookieNames

_T = TypeVar("_T")


class NoneValueError(Exception):
    """Raised when None is passed to getval(value) or await agetval(value)`"""


def getval(value: _T | None) -> _T:
    """
    Returns value if value is not None\n
    Raised:
        - `NoneValueError`
    """
    if value is None:
        raise NoneValueError

    return value


def qualname(obj: object) -> str:
    if isclass(obj):
        return obj.__qualname__

    return obj.__class__.__qualname__


def transform_to_dict(data: list[tuple[str, Any]]) -> dict[str, Any]:  # noqa: C901
    counter: dict[str, int] = {}
    for key, _ in data:
        base_key = key.rstrip("[]")
        counter[base_key] = counter.get(base_key, 0) + 1

    result: dict[str, Any] = {}

    for key, value in data:
        base_key = key.rstrip("[]")
        is_array = key.endswith("[]") or counter[base_key] > 1

        if "." not in base_key:
            if is_array:
                if base_key not in result:
                    result[base_key] = []
                result[base_key].append(value)
            else:
                result[base_key] = value
            continue

        outer_key, inner_key = base_key.split(".", 1)
        if outer_key not in result:
            result[outer_key] = {}
        if is_array:
            if inner_key not in result[outer_key]:
                result[outer_key][inner_key] = []
            result[outer_key][inner_key].append(value)
        else:
            result[outer_key][inner_key] = value

    return result


def remove_empty_values(form_data: dict[str, Any]) -> dict[str, Any]:
    for key, value in form_data.items():
        if value == "":
            form_data[key] = None

        if isinstance(value, UploadFile):
            filename = (value.filename or "").strip()
            if not filename and value.size == 0:
                form_data[key] = None

        if isinstance(value, list):
            form_data[key] = remove_empty_list_items(value)

        if isinstance(value, dict):
            form_data[key] = remove_empty_values(value)

    return form_data


def remove_empty_list_items(items: list[str | UploadFile]) -> list[str | UploadFile]:
    return [
        item
        for item in items
        if (item != "" or (isinstance(item, UploadFile) and not _is_empty_file(item)))
    ]


def _is_empty_file(file: UploadFile) -> bool:
    return (file.filename or "").strip() == "" and file.size == 0


def get_first_query_param_item(request: Request, *, param: str) -> str | None:
    parsed = parse_qs(request.url.query)
    return parsed.get(param, [None])[0]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def set_tokens_to_cookie(
    response: Response,
    *,
    tokens: dict[str, Any],
    token_names: TokenCookieNames,
    path: str,
) -> None:
    now = utc_now()
    response.set_cookie(
        key=token_names.access,
        value=tokens["access_token"],
        secure=True,
        httponly=True,
        expires=now + timedelta(seconds=tokens["expires_in"]),
        samesite="lax",
        path=path,
    )
    response.set_cookie(
        key=token_names.refresh,
        value=tokens["refresh_token"],
        secure=True,
        httponly=True,
        expires=now + timedelta(seconds=tokens["refresh_expires_in"]),
        samesite="lax",
        path=path,
    )


_TOKENS_FIELD_NAME = "__tokens__"


def set_tokens_to_state(
    request: Request,
    *,
    tokens: dict[str, Any],
    token_names: TokenCookieNames,
) -> None:
    setattr(
        request.state,
        _TOKENS_FIELD_NAME,
        {
            token_names.access: tokens["access_token"],
            token_names.refresh: tokens["refresh_token"],
        },
    )


def _get_tokens_from_state(
    request: Request,
    *,
    token_name: str,
) -> str | None:
    result = getattr(request.state, _TOKENS_FIELD_NAME, {}).get(token_name)
    return cast("str | None", result)


def get_tokens_from_request(request: Request, token_name: str) -> str | None:
    from_cookie = request.cookies.get(token_name)
    if from_cookie:
        return from_cookie

    return _get_tokens_from_state(request, token_name=token_name)
