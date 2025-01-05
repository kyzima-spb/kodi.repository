from __future__ import annotations
import logging

import xbmc
import xbmcaddon


__all__ = ('init_logger',)


ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')


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
    handler = KodiLogHandler(level)
    handler.setFormatter(logging.Formatter(f'%(levelname)s [{ADDON_ID}][%(name)s] %(message)s'))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
