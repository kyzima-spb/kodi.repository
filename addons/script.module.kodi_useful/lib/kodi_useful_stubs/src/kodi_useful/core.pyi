import typing as t
from _typeshed import Incomplete

__all__ = ['Addon', 'QueryParams', 'Router']

F = t.TypeVar('F', bound=t.Callable[..., t.Any])

class Addon:
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
    def get_instance(cls, addon_id: str | None = None) -> Addon | None: ...
    def get_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin files."""
    def localize(self, string_id: str | int, fallback: str = '') -> str:
        """Returns the translation for the passed identifier."""
    def route(self, func_or_none: F | None = None, is_root: bool = False) -> t.Callable[[F], F]:
        """
        Adds a handler for the page.

        Arguments:
            func_or_none (callable): Handler function.
            is_root (bool): This is the root page.
        """

class QueryParams:
    def __init__(self, query_string: str) -> None: ...
    def __iter__(self) -> t.Iterator[tuple[str, str | list[str]]]: ...
    def get(self, name: str, default: t.Any | list[t.Any] | None = None, type_cast: t.Callable[[str], t.Any] = ...) -> t.Any | list[t.Any] | None: ...
    def get_bool(self, name: str, default: bool | list[bool] | None = None) -> bool | list[bool] | None: ...
    def get_int(self, name: str, default: int | list[int] | None = None) -> int | list[int] | None: ...
    def get_string(self, name: str, default: str | list[str] | None = None) -> str | list[str] | None: ...
    def set(self, name: str, value: t.Any) -> None: ...

class Router:
    addon: Incomplete
    route_param_name: Incomplete
    plugin_url: Incomplete
    def __init__(self, addon: Addon, plugin_url: str = '', route_param_name: str = 'r') -> None:
        """
        Arguments:
            plugin_url str the plugin url in plugin:// notation.
        """
    def dispatch(self, qs: str = '') -> None:
        """
        Processes a request for a page.

        Arguments:
            qs (str): Query string.
        :return:
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
        '''
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            action str
            kwargs dict "argument=value" pairs
        '''
