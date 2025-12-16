from dataclasses import KW_ONLY, dataclass

from pydantic import BaseModel

JsonType = None | int | str | bool | list["JsonType"] | dict[str, "JsonType"]


@dataclass(frozen=True, slots=True)
class AsJsonResponse:
    response: BaseModel | JsonType
    _: KW_ONLY
    message: str | None = None

    def dump(self) -> "AsJsonResponse":
        if isinstance(self.response, BaseModel):
            return AsJsonResponse(
                response=self.response.model_dump(mode="json"),
                message=self.message,
            )

        return self
