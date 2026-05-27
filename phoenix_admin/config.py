from dataclasses import dataclass
from typing import Annotated

from typing_extensions import Doc


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewConfigBase:
    title: Annotated[str | None, Doc("Represented name")] = None
    icon: Annotated[str | None, Doc('Tabler.io icons. Example: "ti ti-home"')] = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewConfig(ViewConfigBase):
    name: Annotated[str, Doc("View name for identification with url_path_for")]
    submit_button_text: str | None = None
    path: Annotated[str | None, Doc("Url path")] = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelViewConfig(ViewConfigBase):
    page_limit: Annotated[int, Doc("Limit for items in list page")] = 30
