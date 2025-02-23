import typing as t
from .utils import Argument
from _typeshed import Incomplete
from dataclasses import dataclass

__all__ = ['Addon', 'QueryParams', 'Router']

F = t.TypeVar('F', bound=t.Callable[..., t.Any])

@dataclass
class Route:
    name: str
    handler: t.Callable[..., None]
    _arguments: t.Sequence['Argument'] | None = ...
    @property
    def arguments(self) -> t.Sequence['Argument']: ...
    def __init__(self, name, handler) -> None: ...

class Addon:
    _instances: t.ClassVar[dict[str, 'Addon']]
    addon: Incomplete
    id: Incomplete
    addon_dir: Incomplete
    addon_data_dir: Incomplete
    locale_map: Incomplete
    debug: Incomplete
    logger: Incomplete
    url: Incomplete
    handle: Incomplete
    query: Incomplete
    router: Incomplete
    def __init__(self, addon_id: str | None = None, locale_map: dict[str, int] | None = None, locale_map_file: str | None = None, debug: bool = False) -> None: ...
    def error_handler(self, exc_type: type[Exception]) -> t.Callable[[F], F]:
        """Adds a handler for the passed exception type."""
    def get_data_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin user files."""
    @classmethod
    def get_instance(cls, addon_id: str | None = None) -> Addon: ...
    def get_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin files."""
    def get_setting(self, id_: str, type_: str = 'str') -> t.Any:
        """
        Returns the value of a setting as a passed type.

        Arguments:
            id_ (str): id of the setting.
            type_ (str): type of the setting.
        """
    def localize(self, string_id: str | int, *args: t.Any, fallback: str = '', **kwargs: t.Any) -> str:
        """Returns the translation for the passed identifier."""
    @classmethod
    def route(cls, func_or_none: F | None = None, is_root: bool = False) -> t.Callable[[F], F]:
        """
        Adds a handler for the page.

        Arguments:
            func_or_none (callable): Handler function.
            is_root (bool): This is the root page.
        """
    @classmethod
    def url_for(cls, func_or_name: str | t.Callable[..., None], **kwargs: t.Any) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
            kwargs (dict): Query string parameters.
        """
T = t.TypeVar('T')

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

class Router:
    _routes: Incomplete
    _error_handlers: Incomplete
    addon: Incomplete
    route_param_name: Incomplete
    plugin_url: Incomplete
    def __init__(self, addon: Addon, plugin_url: str = '', route_param_name: str = 'r') -> None:
        """
        Arguments:
            plugin_url (str): The plugin url in plugin:// notation.
        """
    def _get_route_name(self, handler: t.Callable[..., None]) -> str:
        """Returns the route name from the callable object."""
    def _handle_exception(self, err: Exception) -> None:
        """Handles the exception if possible, or rethrows it."""
    def dispatch(self, qs: str = '') -> None:
        """
        Processes a request for a page.

        Arguments:
            qs (str): Query string.
        :return:
        """
    def find_route(self, func_or_name: str | t.Callable[..., None]) -> Route:
        """
        Returns the route object for the passed handler.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
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
    def url_for(self, func_or_name: str | t.Callable[..., None], **kwargs: t.Any) -> str:
        """
        Returns a URL for calling the plugin from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
            kwargs (dict): Query string parameters.
        """
