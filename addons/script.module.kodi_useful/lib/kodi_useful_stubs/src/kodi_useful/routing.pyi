import typing as t
from .core import Addon
from .introspection import Parameter
from _typeshed import Incomplete

__all__ = ['router', 'QueryParams', 'Router']

_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])
_T = t.TypeVar('_T')

class QueryParams:
    _params: Incomplete
    def __init__(self, query_string: str) -> None: ...
    def get(self, name: str, required: bool = False, default: t.Any | None = None, type_cast: t.Callable[[str], t.Any] | None = None) -> t.Any | None: ...
    def get_bool(self, name: str, default: bool | None = None) -> bool | None: ...
    @t.overload
    def get_int(self, name: str) -> int | None: ...
    @t.overload
    def get_int(self, name: str, default: None) -> int | None: ...
    @t.overload
    def get_int(self, name: str, default: int) -> int: ...
    def get_int_list(self, name: str, default: list[int] | None = None) -> list[int] | None: ...
    def get_list(self, name: str, required: bool = False, default: list[t.Any] | None = None, type_cast: t.Callable[[str], t.Any] | None = None) -> list[t.Any]: ...
    def to_dict(self) -> dict[str, str | list[str]]:
        """Returns the query string parameters as a dictionary."""

class Route(t.NamedTuple):
    name: str
    handler: t.Callable[..., None]
    @property
    def arguments(self) -> t.Sequence[Parameter]: ...

class Router:
    _routes: Incomplete
    _error_handlers: Incomplete
    route_param_name: Incomplete
    def __init__(self, route_param_name: str = 'r') -> None:
        """
        Arguments:
            route_param_name (str):
                The name of the query string parameter to specify the route name.
        """
    def _get_route_name(self, handler: t.Callable[..., None]) -> str:
        """Returns the route name from the callable object."""
    def _handle_exception(self, err: Exception) -> None:
        """Handles the exception if possible, or rethrows it."""
    def dispatch(self, addon: Addon, query: QueryParams) -> None:
        """
        Processes a request.

        Arguments:
            addon (Addon): The object of the current plugin.
            query (str): Query string.
        """
    def find_route(self, func_or_name: str | t.Callable[..., None]) -> Route:
        """
        Returns the route object for the passed handler.

        Arguments:
            func_or_name (str|Callable):
                A reference to the handler function or a string to import it.
        """
    def register_error_handler(self, exc_type: type[Exception], handler: t.Callable[..., None]) -> None:
        """Adds a handler for the passed exception type."""
    def register_route(self, handler: t.Callable[..., None], is_root: bool = False) -> None:
        """
        Adds a handler for the page.

        Arguments:
            handler (callable): Handler function.
            is_root (bool): This is the root page.
        """
    def route(self, func_or_none: _F | None = None, is_root: bool = False) -> t.Callable[[_F], _F]:
        """
        Adds a handler for the page.

        Arguments:
            func_or_none (callable): Handler function.
            is_root (bool): This is the root page.
        """
    def url_for(self, func_or_name: str | t.Callable[..., None], base_url: str = '', **kwargs: t.Any) -> str:
        """
        Returns a URL for calling the plugin from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable):
                A reference to the handler function or a string to import it.
            base_url (str):
                The base URL for all returned URLs.
            kwargs (dict): Query string parameters.
        """

router: Incomplete
