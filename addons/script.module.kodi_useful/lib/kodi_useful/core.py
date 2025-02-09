import sys
from contextlib import suppress
import configparser
import inspect
import logging
import json
import os
import typing as t
from urllib.parse import parse_qs, urlencode

import xbmc
from xbmcvfs import translatePath

from . import utils


__all__ = (
    'Addon',
    'QueryParams',
    'Router',
)


F = t.TypeVar('F', bound=t.Callable[..., t.Any])


def cast_bool(v: str) -> bool:
    return configparser.ConfigParser.BOOLEAN_STATES.get(v, bool(v))


def loads(v: str) -> t.Any:
    with suppress(json.JSONDecodeError):
        v = json.loads(v)
    return v


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
        self.router = Router(self)

        self.logger.debug(f'URL: {self.url} | HANDLE: {self.handle}')

    def error_handler(self, exc_type: t.Type[Exception]) -> t.Callable[[F], F]:
        """Adds a handler for the passed exception type."""
        def decorator(handler: F) -> F:
            self.router.register_error_handler(exc_type, handler)
            return handler
        return decorator

    def get_data_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin user files."""
        return os.path.join(self.addon_data_dir, name, *paths)

    @classmethod
    def get_instance(cls, addon_id: t.Optional[str] = None) -> t.Optional['Addon']:
        return cls._instances.get(str(addon_id))

    def get_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin files."""
        return os.path.join(self.addon_dir, name, *paths)

    def localize(self, string_id: t.Union[str, int], fallback: str = '') -> str:
        """Returns the translation for the passed identifier."""
        if not fallback:
            fallback = str(string_id)

        if not isinstance(string_id, int):
            string_id = self.locale_map.get(string_id, -1)

        if string_id < 0:
            return fallback

        source = self.addon if 30000 <= string_id < 31000 else xbmc
        result = source.getLocalizedString(string_id)

        return result if result else fallback

    def route(
        self,
        func_or_none: t.Optional[F] = None,
        is_root: bool = False,
    ) -> t.Callable[[F], F]:
        """
        Adds a handler for the page.

        Arguments:
            func_or_none (callable): Handler function.
            is_root (bool): This is the root page.
        """
        def decorator(func: F) -> F:
            self.router.register_route(func, is_root=is_root)
            return func

        if func_or_none is not None:
            return decorator(func_or_none)

        return decorator


class QueryParams:
    def __init__(self, query_string: str) -> None:
        query_string = query_string.strip('?')
        self._params = {
            k: v if len(v) > 1 else v[0]
            for k, v in parse_qs(query_string, keep_blank_values=True).items()
        }

    def __iter__(self) -> t.Iterator[t.Tuple[str, t.Union[str, t.List[str]]]]:
        return iter(self._params.items())

    def get(
        self,
        name: str,
        default: t.Optional[t.Union[t.Any, t.List[t.Any]]] = None,
        type_cast: t.Callable[[str], t.Any] = loads,
    ) -> t.Optional[t.Union[t.Any, t.List[t.Any]]]:
        value = self.get_string(name)

        if value is None:
            return default

        if isinstance(value, list):
            value = [type_cast(i) for i in value]
        else:
            value = type_cast(value)

        return value

    def get_bool(
        self,
        name: str,
        default: t.Optional[t.Union[bool, t.List[bool]]] = None,
    ) -> t.Optional[t.Union[bool, t.List[bool]]]:
        return self.get(name, default, type_cast=cast_bool)

    def get_int(
        self,
        name: str,
        default: t.Optional[t.Union[int, t.List[int]]] = None,
    ) -> t.Optional[t.Union[int, t.List[int]]]:
        return self.get(name, default, type_cast=int)

    def get_string(
        self,
        name: str,
        default: t.Optional[t.Union[str, t.List[str]]] = None,
    ) -> t.Optional[t.Union[str, t.List[str]]]:
        return self._params.get(name, default)

    def set(self, name: str, value: t.Any) -> None:
        self._params[name] = value


class Router:
    def __init__(
        self,
        addon: Addon,
        plugin_url: str = '',
        route_param_name: str = 'r',
    ) -> None:
        """
        Arguments:
            plugin_url str the plugin url in plugin:// notation.
        """
        self._routes: t.Dict[str, t.Callable[..., None]] = {}
        self._error_handlers: t.Dict[t.Type[Exception], t.Callable[..., None]] = {}

        self.addon = addon
        self.route_param_name = route_param_name

        self.plugin_url = plugin_url or self.addon.url

    def _handle_exception(self, err: Exception) -> None:
        """Handles the exception if possible, or rethrows it."""
        for exc_type in type(err).__mro__:
            if exc_type in self._error_handlers:
                handler = self._error_handlers[exc_type]
                return handler(err, self)
        return None

    def dispatch(self, qs: str = '') -> None:
        """
        Processes a request for a page.

        Arguments:
            qs (str): Query string.
        :return:
        """
        q = QueryParams(qs) if qs else self.addon.query
        route_name = q.get_string(self.route_param_name, '')

        if isinstance(route_name, list):
            self.addon.logger.error(f'Passed multiple values for {self.route_param_name}.')
            return None

        if route_name not in self._routes:
            self.addon.logger.error('Route not found.')
            return None

        handler = self._routes[route_name]
        handler_kwargs = {}
        sig = inspect.signature(handler)

        for name, param in sig.parameters.items():
            default = None if param.default is inspect.Parameter.empty else param.default

            if param.annotation is inspect.Parameter.empty:
                handler_kwargs[name] = q.get(name, default=default)
            else:
                handler_kwargs[name] = q.get(name, default=default, type_cast=param.annotation)

        try:
            return handler(**handler_kwargs)
        except Exception as err:
            return self._handle_exception(err)

    def register_error_handler(self, exc_type: t.Type[Exception], handler: t.Callable[..., None]) -> None:
        """Adds a handler for the passed exception type."""
        self._error_handlers[exc_type] = handler

    def register_route(self, handler: t.Callable[..., None], is_root: bool = False) -> None:
        """
        Adds a handler for the page.

        Arguments:
            handler (callable): Handler function.
            is_root (bool): This is the root page.
        """
        name = '%s.%s' % (handler.__module__, handler.__qualname__)

        if name in self._routes:
            self.addon.logger.debug("Duplicate route name '%s'", name)

        self._routes[name] = handler

        if is_root:
            self._routes[''] = handler

    def url_for(
        self,
        func_or_name: t.Union[str, t.Callable[..., None]],
        **kwargs: t.Any,
    ) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            action str
            kwargs dict "argument=value" pairs
        """
        content_type = self.addon.query.get_string('content_type')

        if content_type is not None:
            kwargs['content_type'] = content_type

        if callable(func_or_name):
            for name, func in self._routes.items():
                if func is func_or_name:
                    kwargs[self.route_param_name] = name
                    break
            else:
                raise RuntimeError('The passed argument func is not a route handler.')
        else:
            if func_or_name not in self._routes:
                raise RuntimeError('The passed argument is not a route name.')
            kwargs[self.route_param_name] = func_or_name

        return '%s?%s' % (self.plugin_url, urlencode(kwargs))

    # def url_from_current(self, **kwargs: t.Any) -> str:
    #     q = QueryParams(sys.argv[2][1:])
    #
    #     for name, value in kwargs.items():
    #         q.set(name, value)
    #
    #     return '%s?%s' % (self.plugin_url, urlencode(dict(q)))
