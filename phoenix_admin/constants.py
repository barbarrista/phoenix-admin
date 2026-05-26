from types import SimpleNamespace
from typing import Final

STATICS_ROUTE_NAME: Final = "statics"
INDEX_ROUTE_NAME: Final = "index"
USER_SCOPE_KEY: Final = "user"


class StaticRoute(SimpleNamespace):
    list = "list"
    detail = "detail"
    create = "create"
    update = "update"
    api = "api"
