import enum


class RequestAction(enum.StrEnum):
    list = enum.auto()
    detail = enum.auto()
    create = enum.auto()
    update = enum.auto()
    custom = enum.auto()
    api = enum.auto()
