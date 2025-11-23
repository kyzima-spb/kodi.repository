import logging
import json
import os
import sys
import typing as t

import xbmc
import xbmcvfs

from . import utils
from .routing import router, QueryParams


__all__ = (
    'current_addon',
    'Addon',
)


F = t.TypeVar('F', bound=t.Callable[..., t.Any])


class Addon:
    _instances: t.ClassVar[t.Dict[str, 'Addon']] = {}

    def __init__(
        self,
        addon_id: t.Optional[str] = None,
        *,
        debug: bool = False,
    ) -> None:
        self.addon = utils.get_addon(addon_id)
        self.id = addon_id or self.addon.getAddonInfo('id')

        self.addon_dir = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.addon_data_dir = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))

        locale_map_file = self.get_path('resources', 'language', 'locale_map.json')

        if xbmcvfs.exists(locale_map_file):
            with open(locale_map_file) as f:
                self.locale_map = json.load(f)
        else:
            self.locale_map = {}

        self.debug = debug or utils.debug_argument_passed()

        if self.debug:
            self.logger = utils.get_logger(self.id, logging.DEBUG)
        else:
            self.logger = utils.get_logger(self.id)

        self.url = sys.argv[0] if len(sys.argv) > 0 else ''
        self.handle = int(sys.argv[1]) if len(sys.argv) > 1 else 0
        self.query = QueryParams(sys.argv[2] if len(sys.argv) > 2 else '')
        self.router = router

        self.logger.debug(f'URL: {self.url} | Query: {self.query.to_dict()} | HANDLE: {self.handle}')

    def dispatch(self, query: t.Optional[QueryParams] = None) -> None:
        """Processes a request."""
        if query is None:
            query = self.query
        return self.router.dispatch(self, query)

    def error_handler(self, exc_type: t.Type[Exception]) -> t.Callable[[F], F]:
        """Adds a handler for the passed exception type."""
        def decorator(handler: F) -> F:
            self.router.register_error_handler(exc_type, handler)
            return handler
        return decorator

    def get_data_path(self, *paths: str, translate: bool = True) -> str:
        """Returns the path to the plugin user files."""
        return self.get_path(*paths, translate=translate, id_='profile')

    @classmethod
    def get_instance(cls, addon_id: t.Optional[str] = None) -> 'Addon':
        key = addon_id or ''

        if key not in cls._instances:
            cls._instances[key] = cls(addon_id)

        return cls._instances[key]

    def get_path(self, *paths: str, translate=True, id_: str = 'path') -> str:
        """Returns the path to the plugin files."""
        path = os.path.join(self.addon.getAddonInfo(id_), *paths)

        if translate:
            path = xbmcvfs.translatePath(path)

        return path

    def get_setting(
        self,
        id_: str,
        type_: t.Union[t.Type, t.Callable[[str], t.Any]] = str,
    ) -> t.Any:
        """
        Returns the value of a setting as a passed type.

        Arguments:
            id_ (str): id of the setting.
            type_ (type|Callable): type of the setting.
        """
        if issubclass(type_, bool):
            return self.addon.getSettingBool(id_)
        elif issubclass(type_, float):
            return self.addon.getSettingNumber(id_)
        elif issubclass(type_, int):
            return self.addon.getSettingInt(id_)
        elif issubclass(type_, str):
            return self.addon.getSetting(id_)
        else:
            return type_(self.addon.getSetting(id_))

    def set_setting(self, id_: str, value: t.Any) -> None:
        """
        Save the value of a setting.

        Arguments:
            id_ (str): id of the setting.
            value: value of the setting.
        """
        if isinstance(value, bool):
            self.addon.setSettingBool(id_, value)
        elif isinstance(value, int):
            self.addon.setSettingInt(id_, value)
        else:
            self.addon.setSettingString(id_, value)

    def localize(
        self,
        string_id: t.Union[str, int],
        *args: t.Any,
        fallback: str = '',
        **kwargs: t.Any,
    ) -> str:
        """Returns the translation for the passed identifier."""
        if not fallback:
            fallback = str(string_id)

        if not isinstance(string_id, int):
            string_id = self.locale_map.get(string_id.lower(), -1)

        if string_id < 0:
            result = fallback
        else:
            source = self.addon if 30000 <= string_id < 31000 else xbmc
            result = source.getLocalizedString(string_id) or fallback

        if args:
            return result % args

        if kwargs:
            return result % kwargs

        return result

    def url_for(
        self,
        func_or_name: t.Union[str, t.Callable[..., None]],
        **kwargs: t.Any,
    ) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
            kwargs (dict): Query string parameters.
        """
        if not kwargs.get('content_type'):
            content_type = self.query.get('content_type')

            if content_type is not None:
                kwargs['content_type'] = content_type

        return self.router.url_for(func_or_name, base_url=self.url, **kwargs)


current_addon = Addon.get_instance()
