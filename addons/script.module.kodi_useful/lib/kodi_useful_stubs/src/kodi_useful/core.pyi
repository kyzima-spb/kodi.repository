import typing as t
from .routing import QueryParams
from _typeshed import Incomplete

__all__ = ['current_addon', 'Addon']

F = t.TypeVar('F', bound=t.Callable[..., t.Any])

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
    def dispatch(self, query: QueryParams | None = None) -> None:
        """Processes a request."""
    def error_handler(self, exc_type: type[Exception]) -> t.Callable[[F], F]:
        """Adds a handler for the passed exception type."""
    def get_data_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin user files."""
    @classmethod
    def get_instance(cls, addon_id: str | None = None) -> Addon: ...
    def get_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin files."""
    def get_setting(self, id_: str, type_: type | t.Callable[[str], t.Any] = ...) -> t.Any:
        """
        Returns the value of a setting as a passed type.

        Arguments:
            id_ (str): id of the setting.
            type_ (type|Callable): type of the setting.
        """
    def localize(self, string_id: str | int, *args: t.Any, fallback: str = '', **kwargs: t.Any) -> str:
        """Returns the translation for the passed identifier."""
    def url_for(self, func_or_name: str | t.Callable[..., None], **kwargs: t.Any) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
            kwargs (dict): Query string parameters.
        """

current_addon: Incomplete
