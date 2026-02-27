from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping, Sequence
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, TypeVar

from pydantic import ValidationError
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route

from phoenix_admin.auth.dto import AuthData, AuthenticationResult
from phoenix_admin.auth.exceptions import AuthenticationError
from phoenix_admin.auth.middleware import AuthMiddleware
from phoenix_admin.constants import INDEX_ROUTE_NAME, STATICS_ROUTE_NAME
from phoenix_admin.exceptions import FormValidationError
from phoenix_admin.state import get_app_state
from phoenix_admin.views.form_validation.pydantic_ import get_form_errors

if TYPE_CHECKING:
    from phoenix_admin.admin import AdminApp

_TResponse = TypeVar("_TResponse", bound=Response)


def create_endpoint_handler(
    endpoint: Callable[..., Awaitable[Response]],
    **kwargs: Any,  # noqa: ANN401,
) -> Callable[[Request], Awaitable[Response]]:
    async def wrapper(request: Request) -> Response:
        return await endpoint(request=request, **kwargs)

    return wrapper


class BaseAuthProvider(ABC):
    def __init__(
        self,
        sign_in_path: str = "/sign-in",
        sign_out_path: str = "/sign-out",
    ) -> None:
        self._sign_in_path: Final = sign_in_path
        self.sign_in_route_name: Final = "sign_in"

        self._sign_out_path: Final = sign_out_path
        self.sign_out_route_name: Final = "sign_out"

        self._default_context: Final[Mapping[str, Any]] = {"is_auth_case": True}

    @property
    def not_login_required_routes(self) -> list[str]:
        return [self.sign_in_route_name, self.sign_out_route_name, STATICS_ROUTE_NAME]

    @property
    def routes_for_redirect_to_index(self) -> list[str]:
        return [self.sign_in_route_name]

    @abstractmethod
    async def get_sign_in_response(self, request: Request) -> Response:
        raise NotImplementedError

    @abstractmethod
    async def get_sign_out_response(self, request: Request) -> Response:
        raise NotImplementedError

    @abstractmethod
    async def authenticate(self, request: Request) -> AuthenticationResult:
        raise NotImplementedError

    def _get_sign_in_route(self) -> Route:
        return Route(
            self._sign_in_path,
            create_endpoint_handler(self.get_sign_in_response),
            methods=[HTTPMethod.GET, HTTPMethod.POST],
            name=self.sign_in_route_name,
        )

    def _get_sign_out_route(self) -> Route:
        return Route(
            self._sign_out_path,
            create_endpoint_handler(self.get_sign_out_response),
            methods=[HTTPMethod.GET, HTTPMethod.POST],
            name=self.sign_out_route_name,
        )

    def add_routes_to_app(self, admin_app: "AdminApp") -> None:
        admin_app.asgi_app.routes.extend(
            (
                self._get_sign_in_route(),
                self._get_sign_out_route(),
            )
        )

    def get_depends_middlewares(self, admin_app: "AdminApp") -> Sequence[Middleware]:  # noqa: ARG002
        return [Middleware(AuthMiddleware, provider=self)]


class FormAuthProvider(BaseAuthProvider):
    @abstractmethod
    async def sign_in(self, form_data: AuthData, *, request: Request) -> None:
        raise NotImplementedError

    async def after_sign_in(self, request: Request, response: _TResponse) -> _TResponse:  # noqa: ARG002
        return response

    @abstractmethod
    async def sign_out(self, request: Request) -> None:
        raise NotImplementedError

    async def after_sign_out(
        self,
        request: Request,  # noqa: ARG002
        response: _TResponse,
    ) -> _TResponse:
        return response

    async def get_sign_in_response(self, request: Request) -> Response:
        state = get_app_state(request)
        template_name = "sign_in.html"
        if request.method == HTTPMethod.GET:
            return state.admin_app.templates.TemplateResponse(  # type: ignore[no-any-return]
                request=request,
                name=template_name,
                context=self._default_context,  # type: ignore[call-overload]
            )

        try:
            form_data = await self._get_form_data(request)
            await self.sign_in(form_data, request=request)

        except (ValidationError, FormValidationError) as exc:
            form_errors = (
                get_form_errors(exc) if isinstance(exc, ValidationError) else exc.errors
            )
            return state.admin_app.templates.TemplateResponse(
                request=request,
                name=template_name,
                context={
                    "form_errors": FormValidationError(form_errors),
                    **self._default_context,
                },
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        except AuthenticationError as exc:
            return state.admin_app.templates.TemplateResponse(
                request=request,
                name=template_name,
                context={"error_message": exc.message, **self._default_context},
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        response = RedirectResponse(
            request.query_params.get("next")
            or request.url_for(state.admin_route_name + f":{INDEX_ROUTE_NAME}"),
            status_code=HTTPStatus.SEE_OTHER,
        )
        response = await self.after_sign_in(request=request, response=response)
        return response  # noqa: RET504

    async def get_sign_out_response(self, request: Request) -> Response:
        state = get_app_state(request)
        response = RedirectResponse(
            request.url_for(state.admin_route_name + f":{INDEX_ROUTE_NAME}"),
            status_code=HTTPStatus.SEE_OTHER,
        )
        await self.sign_out(request)
        response = await self.after_sign_out(request=request, response=response)
        return response  # noqa: RET504

    async def _get_form_data(self, request: Request) -> AuthData:
        return AuthData.model_validate(await request.form())
