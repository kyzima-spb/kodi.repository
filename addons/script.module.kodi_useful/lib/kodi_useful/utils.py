import configparser
from contextlib import suppress
import logging
import json
import os
import sys
import typing as t

import xbmc
import xbmcaddon


__all__ = (
    'auto_cast',
    'cast_bool',
    'get_addon',
    'get_logger',
)


def auto_cast(v: str) -> t.Any:
    """Attempts to cast a string value to a known JSON type, otherwise returns the original string."""
    with suppress(json.JSONDecodeError):
        v = json.loads(v)
    return v


def cast_bool(v: str) -> bool:
    """Casts a string to a boolean type by parsing the value."""
    return configparser.ConfigParser.BOOLEAN_STATES.get(v, bool(v))


def debug_argument_passed() -> bool:
    return '--debug' in os.environ.get('KODI_EXTRA_ARGS', '')


def get_addon(addon_id: t.Optional[str] = None) -> xbmcaddon.Addon:
    """
    Returns the plugin object.

    If no name is passed, returns the current plugin.

    Arguments:
        addon_id (str): Kodi plugin name.
    """
    if addon_id is not None:
        return xbmcaddon.Addon(addon_id)
    return xbmcaddon.Addon()


def get_logger(
    addon_id: t.Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Initializes and returns an instance of the logger.

    Arguments:
        addon_id (str): Kodi plugin name.
        level (str): The level of messages displayed in the log.
    """
    if addon_id is None:
        addon_id = get_addon().getAddonInfo('id')

    handler = KodiLogHandler(level)
    handler.setFormatter(logging.Formatter(f'%(levelname)s [%(name)s][%(import_name)s] %(message)s'))

    logger = logging.getLogger(addon_id)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addFilter(ImportNameFilter())

    return logger


class ImportNameFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.import_name = record.module

        for name in sys.modules:
            if sys.modules[name] and getattr(sys.modules[name], '__file__', None) == record.pathname:
                record.import_name = name
                break

        return True


class KodiLogHandler(logging.Handler):
    levels_map = {
        logging.CRITICAL: xbmc.LOGFATAL,
        logging.ERROR: xbmc.LOGERROR,
        logging.WARNING: xbmc.LOGWARNING,
        logging.INFO: xbmc.LOGINFO,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.NOTSET: xbmc.LOGNONE,
    }

    def emit(self, record: logging.LogRecord) -> None:
        xbmc.log(self.format(record), self.levels_map[record.levelno])
