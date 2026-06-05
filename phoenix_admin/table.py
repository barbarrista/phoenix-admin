from pydantic import BaseModel, RootModel


class TableColumnProps(BaseModel):
    id: str | None = None
    name: str | None = None
    width: str | None = None
    """200px or 30%"""
    sort: bool = True
    hidden: bool = False


class TableColumnPropsList(RootModel[list[TableColumnProps]]):
    pass
