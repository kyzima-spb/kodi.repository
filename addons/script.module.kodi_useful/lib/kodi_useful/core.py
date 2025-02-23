import inspect
from dataclasses import dataclass, field
import logging
import json
import os
import sys
import typing as t
from urllib.parse import parse_qs, urlencode

import xbmc
from xbmcvfs import translatePath

from . import utils
from .enums import Scope

if t.TYPE_CHECKING:
    from .utils import Argument


__all__ = (
    'Addon',
    'QueryParams',
    'Router',
)


F = t.TypeVar('F', bound=t.Callable[..., t.Any])


@dataclass
class Route:
    name: str
    handler: t.Callable[..., None]
    _arguments: t.Optional[t.Sequence['Argument']] = field(init=False, default=None)

    @property
    def arguments(self) -> t.Sequence['Argument']:
        if self._arguments is None:
            self._arguments = utils.get_function_arguments(self.handler)
        return self._arguments


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

        self.logger.debug(f'URL: {self.url} | Query: {self.query.to_dict()} | HANDLE: {self.handle}')

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
    def get_instance(cls, addon_id: t.Optional[str] = None) -> 'Addon':
        addon_id = str(addon_id)

        if addon_id not in cls._instances:
            raise ValueError(f'Addon with {addon_id!r} not found.')

        return cls._instances[addon_id]

    def get_path(self, name: str, *paths: str) -> str:
        """Returns the path to the plugin files."""
        return os.path.join(self.addon_dir, name, *paths)

    def get_setting(self, id_: str, type_: str = 'str') -> t.Any:
        """
        Returns the value of a setting as a passed type.

        Arguments:
            id_ (str): id of the setting.
            type_ (str): type of the setting.
        """
        getters_map = {
            'bool': self.addon.getSettingBool,
            'float': self.addon.getSettingNumber,
            'int': self.addon.getSettingInt,
            'str': self.addon.getSetting,
        }
        return getters_map[type_](id_)

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

    @classmethod
    def route(
        cls,
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
            current_addon = cls.get_instance() if isinstance(cls, type) else cls
            current_addon.router.register_route(func, is_root=is_root)
            return func

        if func_or_none is not None:
            return decorator(func_or_none)

        return decorator

    @classmethod
    def url_for(
        cls,
        func_or_name: t.Union[str, t.Callable[..., None]],
        **kwargs: t.Any,
    ) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
            kwargs (dict): Query string parameters.
        """
        current_addon = cls.get_instance() if isinstance(cls, type) else cls
        return current_addon.router.url_for(func_or_name, **kwargs)


T = t.TypeVar('T')


class QueryParams:
    def __init__(self, query_string: str) -> None:
        query_string = query_string.strip('?')
        self._params = parse_qs(query_string, keep_blank_values=True)

    # @t.overload
    # def get(self, name: str) -> t.Optional[t.Any]: ...
    #
    # @t.overload
    # def get(self, name: str, default: T) -> t.Optional[T]: ...

    # @t.overload
    # def get(self, name: str, default: t.Any) -> t.Any: ...

    def get(
        self,
        name: str,
        required: bool = False,
        default: t.Optional[t.Any] = None,
        type_cast: t.Optional[t.Callable[[str], t.Any]] = None,
    ) -> t.Optional[t.Any]:
        value = self.get_list(name, required=required, type_cast=type_cast)
        return value[-1] if len(value) > 0 else default

    def get_bool(self, name: str, default: t.Optional[bool] = None) -> t.Optional[bool]:
        return self.get(name, default=default, type_cast=utils.cast_bool)

    @t.overload
    def get_int(self, name: str) -> t.Optional[int]: ...

    @t.overload
    def get_int(self, name: str, default: None) -> t.Optional[int]: ...

    @t.overload
    def get_int(self, name: str, default: int) -> int: ...

    def get_int(self, name: str, default: t.Optional[int] = None) -> t.Optional[int]:
        return self.get(name, default=default, type_cast=int)

    def get_int_list(self, name: str, default: t.Optional[t.List[int]] = None) -> t.Optional[t.List[int]]:
        return self.get_list(name, default=default, type_cast=int)

    def get_list(
        self,
        name: str,
        required: bool = False,
        default: t.Optional[t.List[t.Any]] = None,
        type_cast: t.Optional[t.Callable[[str], t.Any]] = None,
    ) -> t.List[t.Any]:
        if name not in self._params:
            if required:
                raise ValueError(f'The {name!r} parameter is missing in the query string.')

            if default is None:
                default = []

            return default

        if type_cast is None:
            return self._params[name]

        return [type_cast(i) for i in self._params[name]]

    def to_dict(self) -> t.Dict[str, t.Union[str, t.List[str]]]:
        """Returns the query string parameters as a dictionary."""
        return {k: v[0] if len(v) == 1 else v for k, v in self._params.items()}


class Router:
    def __init__(
        self,
        addon: Addon,
        plugin_url: str = '',
        route_param_name: str = 'r',
    ) -> None:
        """
        Arguments:
            plugin_url (str): The plugin url in plugin:// notation.
        """
        self._routes: t.Dict[str, Route] = {}
        self._error_handlers: t.Dict[t.Type[Exception], t.Callable[..., None]] = {}

        self.addon = addon
        self.route_param_name = route_param_name

        self.plugin_url = plugin_url or self.addon.url

    def _get_route_name(self, handler: t.Callable[..., None]) -> str:
        """Returns the route name from the callable object."""
        return '%s.%s' % (handler.__module__, handler.__qualname__)

    def _handle_exception(self, err: Exception) -> None:
        """Handles the exception if possible, or rethrows it."""
        for exc_type in type(err).__mro__:
            if exc_type in self._error_handlers:
                handler = self._error_handlers[exc_type]
                return handler(err, self)
        else:
            self.addon.logger.error(f'Uncaught exception: {err!r}')
            raise err

    def dispatch(self, qs: str = '') -> None:
        """
        Processes a request for a page.

        Arguments:
            qs (str): Query string.
        :return:
        """
        q = QueryParams(qs) if qs else self.addon.query
        route_name = q.get(self.route_param_name, default='')
        route = self.find_route(route_name)
        handler_kwargs = {}

        self.addon.logger.debug(route.arguments)

        for arg in route.arguments:
            if arg.type_cast is not None and issubclass(arg.type_cast, Addon):
                handler_kwargs[arg.name] = self.addon
            elif arg.metadata.scope != Scope.NOTSET:
                name = arg.metadata.name or arg.name
                scope = arg.metadata.scope

                if scope == Scope.QUERY:
                    handler_kwargs[arg.name] = q.get(
                        name,
                        required=arg.required,
                        default=arg.default_value,
                        type_cast=arg.type_cast,
                    )
                elif scope == Scope.SETTINGS:
                    handler_kwargs[arg.name] = self.addon.get_setting(name, arg.type_cast.__name__)

        try:
            return route.handler(**handler_kwargs)
        except Exception as err:
            return self._handle_exception(err)

    def find_route(self, func_or_name: t.Union[str, t.Callable[..., None]]) -> Route:
        """
        Returns the route object for the passed handler.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
        """
        if callable(func_or_name):
            name = self._get_route_name(func_or_name)
            route = self._routes.get(name)

            if route is None or route.handler is not func_or_name:
                raise RuntimeError('The passed argument is not a route handler.')

            return route

        if func_or_name not in self._routes:
            raise RuntimeError(f'The passed argument {func_or_name!r} is not a route name.')

        return self._routes[func_or_name]

    def register_error_handler(self, exc_type: t.Type[Exception], handler: t.Callable[..., None]) -> None:
        """Adds a handler for the passed exception type."""
        self._error_handlers[exc_type] = handler

    def register_route(
        self,
        handler: t.Callable[..., None],
        is_root: bool = False,
    ) -> None:
        """
        Adds a handler for the page.

        Arguments:
            handler (callable): Handler function.
            is_root (bool): This is the root page.
        """
        name = self._get_route_name(handler)

        if name in self._routes:
            self.addon.logger.debug("Duplicate route name '%s'", name)

        self._routes[name] = Route(name=name, handler=handler)

        if is_root:
            self._routes[''] = self._routes[name]

    def url_for(
        self,
        func_or_name: t.Union[str, t.Callable[..., None]],
        **kwargs: t.Any,
    ) -> str:
        """
        Returns a URL for calling the plugin from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable): A reference to the handler function or a string to import it.
            kwargs (dict): Query string parameters.
        """
        if not kwargs.get('content_type'):
            content_type = self.addon.query.get('content_type')

            if content_type is not None:
                kwargs['content_type'] = content_type

        route = self.find_route(func_or_name)
        kwargs[self.route_param_name] = route.name

        for arg in route.arguments:
            if arg.metadata.scope == Scope.QUERY and arg.required and arg.name not in kwargs:
                raise ValueError(f'Missing value for required parameter {arg.name!r} in query string.')

        return '%s?%s' % (self.plugin_url, urlencode(kwargs))
