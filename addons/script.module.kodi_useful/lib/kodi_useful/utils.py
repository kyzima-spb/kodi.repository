from __future__ import annotations
import logging
import typing as t

import xbmc
import xbmcaddon


__all__ = (
    'get_addon',
    'init_logger',
)


def get_addon(addon_id: t.Optional[str] = None) -> xbmcaddon.Addon:
    if addon_id is not None:
        return xbmcaddon.Addon(addon_id)
    return xbmcaddon.Addon()


def get_settings(addon_id: t.Optional[str] = None) -> xbmcaddon.Settings:
    return get_addon(addon_id).getSettings()


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


def init_logger(
    name: str | None = None,
    level: int = logging.DEBUG,
) -> None:
    addon_id = get_addon().getAddonInfo('id')

    handler = KodiLogHandler(level)
    handler.setFormatter(logging.Formatter(f'%(levelname)s [{addon_id}][%(name)s] %(message)s'))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
