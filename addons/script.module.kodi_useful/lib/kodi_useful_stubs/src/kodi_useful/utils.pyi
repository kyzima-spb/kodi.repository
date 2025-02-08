import logging
import xbmcaddon
from _typeshed import Incomplete

__all__ = ['get_addon', 'get_logger']

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
