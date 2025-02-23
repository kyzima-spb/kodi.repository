import logging
import typing as t
import xbmcaddon
from .enums import Scope
from _typeshed import Incomplete
from dataclasses import InitVar, dataclass

__all__ = ['auto_cast', 'cast_bool', 'get_addon', 'get_function_arguments', 'get_logger', 'Argument']

class ArgumentMetadata(t.NamedTuple):
    scope: Scope = ...
    name: str = ...

@dataclass
class Argument:
    name: str
    default: t.Any
    annotation: InitVar[t.Any]
    metadata: ArgumentMetadata = ...
    type_cast: t.Callable[[str], t.Any] | None = ...
    def __post_init__(self, annotation: t.Any): ...
    @property
    def default_value(self) -> t.Any: ...
    @property
    def required(self) -> bool: ...
    def __init__(self, name, default, annotation) -> None: ...

def auto_cast(v: str) -> t.Any:
    """Attempts to cast a string value to a known JSON type, otherwise returns the original string."""
def cast_bool(v: str) -> bool:
    """Casts a string to a boolean type by parsing the value."""
def get_function_arguments(func: t.Callable[..., t.Any]) -> t.Sequence[Argument]:
    """
    Returns information about the function arguments:
    name, whether required, default value, and annotation.
    """
def get_addon(addon_id: str | None = None) -> xbmcaddon.Addon:
    """
    Returns the plugin object.

    If no name is passed, returns the current plugin.

    Arguments:
        addon_id (str): Kodi plugin name.
    """
def get_logger(addon_id: str | None = None, level: int = ...) -> logging.Logger:
    """
    Initializes and returns an instance of the logger.

    Arguments:
        addon_id (str): Kodi plugin name.
        level (str): The level of messages displayed in the log.
    """

class ImportNameFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool: ...

class KodiLogHandler(logging.Handler):
    levels_map: Incomplete
    def emit(self, record: logging.LogRecord) -> None: ...
