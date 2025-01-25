import logging
import xbmcaddon
from _typeshed import Incomplete

__all__ = ['get_addon', 'init_logger']

def get_addon(addon_id: str | None = None) -> xbmcaddon.Addon: ...

class KodiLogHandler(logging.Handler):
    levels_map: Incomplete
    def emit(self, record: logging.LogRecord) -> None: ...

def init_logger(name: str | None = None, level: int = ...) -> None: ...
