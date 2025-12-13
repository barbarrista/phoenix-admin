from dataclasses import dataclass
from typing import Annotated

from typing_extensions import Doc


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewConfig:
    name: Annotated[str, Doc("View name for identification with url_path_for")]
    title: Annotated[str | None, Doc("Represented name")] = None
    submit_button_text: str | None = None
    path: Annotated[str, Doc("Url path")] = "/"
    icon: Annotated[str | None, Doc('Tabler.io icons. Example: "ti ti-home"')] = None
