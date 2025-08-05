import logging
import json
import os
import sys
import typing as t

import xbmc
from xbmcvfs import translatePath

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
        locale_map: t.Optional[t.Dict[str, int]] = None,
        locale_map_file: t.Optional[str] = None,
        debug: bool = False,
    ) -> None:
        self._instances[str(addon_id)] = self

        self.addon = utils.get_addon(addon_id)
        self.id = addon_id or self.addon.getAddonInfo('id')

        self.addon_dir = translatePath(self.addon.getAddonInfo('path'))
        self.addon_data_dir = translatePath(self.addon.getAddonInfo('profile'))

        if locale_map_file is not None:
            locale_map_file = self.get_path(locale_map_file)

            with open(locale_map_file) as f:
                locale_map = json.load(f)

        self.locale_map = locale_map or {}
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
        addon_id = str(addon_id)

        if addon_id not in cls._instances:
            raise ValueError(f'Addon with {addon_id!r} not found.')

        return cls._instances[addon_id]

    def get_path(self, *paths: str, translate=True, id_: str = 'path') -> str:
        """Returns the path to the plugin files."""
        path = os.path.join(self.addon.getAddonInfo(id_), *paths)

        if translate:
            path = translatePath(path)

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
            string_id = self.locale_map.get(string_id, -1)

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


current_addon = Addon()
