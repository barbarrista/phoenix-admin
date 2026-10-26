from typing import Literal, cast

import pytest
from phoenix_admin.config import ModelViewConfig
from phoenix_admin.ext.sqla.mappers import RelationshipMapper
from phoenix_admin.ext.sqla.pk import Pk
from phoenix_admin.ext.sqla.view import SqlalchemyModelView
from phoenix_admin.fields.exceptions import ParseError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from starlette.requests import Request
from starlette.types import Scope


class Base(DeclarativeBase):
    pass


class Status(Base):
    __tablename__ = "status"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


def http_request() -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    return Request(cast("Scope", scope))


class StatusView(SqlalchemyModelView[Status]):
    identity = "status"
    pk_field = Pk(Status.id)
    __config__ = ModelViewConfig(page_limit=10)
    fields = ()

    async def repr_model(
        self,
        request: Request,  # noqa: ARG002
        model: Status,
        request_type: Literal["list", "field_access"],  # noqa: ARG002
    ) -> str:
        return model.name


class TrackingView(StatusView):
    def __init__(self) -> None:
        self.seen: list[Request] = []

    async def repr_model(
        self,
        request: Request,
        model: Status,
        request_type: Literal["list", "field_access"],  # noqa: ARG002
    ) -> str:
        self.seen.append(request)
        return model.name


@pytest.mark.asyncio
async def test_collection_joins_item_reprs() -> None:
    result = await RelationshipMapper().to_json(
        [Status(id=1, name="draft"), Status(id=2, name="signed")],
        model_view=StatusView(),
        request=http_request(),
    )

    assert result == "draft, signed"


@pytest.mark.asyncio
async def test_single_model_returns_its_repr() -> None:
    result = await RelationshipMapper().to_json(
        Status(id=1, name="hq"),
        model_view=StatusView(),
        request=http_request(),
    )

    assert result == "hq"


@pytest.mark.asyncio
async def test_repr_model_receives_the_request() -> None:
    request = http_request()
    view = TrackingView()

    result = await RelationshipMapper().to_json(
        Status(id=1, name="hq"),
        model_view=view,
        request=request,
    )

    assert result == "hq"
    assert view.seen == [request]


@pytest.mark.asyncio
async def test_collection_reprs_receive_the_request() -> None:
    request = http_request()
    view = TrackingView()

    result = await RelationshipMapper().to_json(
        [Status(id=1, name="draft"), Status(id=2, name="signed")],
        model_view=view,
        request=request,
    )

    assert result == "draft, signed"
    assert view.seen == [request, request]


@pytest.mark.asyncio
async def test_empty_collection_is_empty_string() -> None:
    result = await RelationshipMapper().to_json(
        [],
        model_view=StatusView(),
        request=http_request(),
    )

    assert result == ""


@pytest.mark.asyncio
async def test_optional_none_returns_none() -> None:
    result = await RelationshipMapper().to_json(
        None,
        is_optional=True,
        model_view=StatusView(),
        request=http_request(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_required_none_raises() -> None:
    with pytest.raises(ParseError):
        await RelationshipMapper().to_json(
            None,
            is_optional=False,
            model_view=StatusView(),
            request=http_request(),
        )
