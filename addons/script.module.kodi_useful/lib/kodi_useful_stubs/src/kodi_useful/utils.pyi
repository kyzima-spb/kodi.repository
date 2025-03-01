import logging
import typing as t
import xbmcaddon
from _typeshed import Incomplete

__all__ = ['auto_cast', 'cast_bool', 'get_addon', 'get_logger', 'get_screen_resolution']

def auto_cast(v: str) -> t.Any:
    """Attempts to cast a string value to a known JSON type, otherwise returns the original string."""
def cast_bool(v: str) -> bool:
    """Casts a string to a boolean type by parsing the value."""
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
def get_screen_resolution() -> tuple[int, int]:
    """Returns the screen resolution set in the settings."""

class ImportNameFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool: ...

class KodiLogHandler(logging.Handler):
    levels_map: Incomplete
    def emit(self, record: logging.LogRecord) -> None: ...
