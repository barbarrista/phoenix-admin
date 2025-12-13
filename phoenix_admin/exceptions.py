class PhoenixAdminError(Exception):
    def __init__(self, msg: str) -> None:
        self.message = msg
