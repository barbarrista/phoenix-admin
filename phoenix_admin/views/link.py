from phoenix_admin.views.base import BaseView


class LinkView(BaseView):
    __slots__ = ("icon", "is_blank", "title", "url")

    def __init__(
        self,
        title: str,
        url: str,
        icon: str | None = None,
        *,
        is_blank: bool = False,
    ) -> None:
        self.title = title
        self.url = url
        self.icon = icon
        self.is_blank = is_blank
