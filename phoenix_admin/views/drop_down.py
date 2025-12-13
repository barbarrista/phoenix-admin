from collections.abc import Sequence

from phoenix_admin.views.base import BaseView, View


class DropDown(BaseView):
    __slots__ = ("icon", "title", "views")

    def __init__(
        self,
        title: str,
        views: Sequence[View],
        icon: str | None = None,
    ) -> None:
        self.title = title
        self.views = views
        self.icon = icon
