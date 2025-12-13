from phoenix_admin.exceptions import PhoenixAdminError


def raise_exception(msg: str) -> None:
    raise PhoenixAdminError(msg)
