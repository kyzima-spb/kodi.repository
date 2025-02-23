import configparser
from contextlib import suppress
from dataclasses import dataclass, InitVar, field
from functools import lru_cache
import inspect
import logging
import json
import os
import sys
import typing as t

import xbmc
import xbmcaddon

from .enums import Scope


__all__ = (
    'auto_cast',
    'cast_bool',
    'get_addon',
    'get_function_arguments',
    'get_logger',
    'Argument',
)


class ArgumentMetadata(t.NamedTuple):
    scope: Scope = Scope.NOTSET
    name: str = ''


@dataclass
class Argument:
    name: str
    default: t.Any
    annotation: InitVar[t.Any]
    metadata: ArgumentMetadata = field(
        init=False,
        default_factory=lambda: ArgumentMetadata(),
    )
    type_cast: t.Optional[t.Callable[[str], t.Any]] = field(default=None, init=False)

    def __post_init__(self, annotation: t.Any):
        if annotation is not inspect.Parameter.empty:
            if hasattr(annotation, '__metadata__'):
                annotation, *metadata = t.get_args(annotation)
                self.metadata = ArgumentMetadata(*metadata)

            origin = t.get_origin(annotation)

            if not origin:
                self.type_cast = annotation

            if origin is t.Union:
                variants = {i for i in t.get_args(annotation) if not isinstance(None, i)}

                if len(variants) == 1:
                    self.type_cast = variants.pop()

            # from kodi_useful import Addon
            # Addon.get_instance().logger.debug(f'{self.name} {self.metadata}')

    @property
    def default_value(self) -> t.Any:
        if self.default is inspect.Parameter.empty:
            return None
        return self.default

    @property
    def required(self) -> bool:
        return self.default is inspect.Parameter.empty


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


@lru_cache
def get_function_arguments(func: t.Callable[..., t.Any]) -> t.Sequence[Argument]:
    """
    Returns information about the function arguments:
    name, whether required, default value, and annotation.
    """
    sig = inspect.signature(func)
    real_types = t.get_type_hints(func, include_extras=True)
    return [
        Argument(name=name, default=param.default, annotation=real_types.get(name, param.annotation))
        for name, param in sig.parameters.items()
    ]


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


def get_settings(addon_id: t.Optional[str] = None) -> xbmcaddon.Settings:
    return get_addon(addon_id).getSettings()


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
