import sys
from contextlib import suppress
import configparser
import logging
import json
import typing as t
from urllib.parse import parse_qs, urlencode


__all__ = (
    'QueryParams',
    'Router',
)

logger = logging.getLogger()


def cast_bool(v: str) -> bool:
    with suppress(KeyError):
        v = configparser.ConfigParser.BOOLEAN_STATES[v]
    return bool(v)


def loads(v):
    with suppress(json.JSONDecodeError):
        v = json.loads(v)
    return v


class QueryParams:
    def __init__(self, query_string: str) -> None:
        query_string = query_string.strip('?')
        self._params = {
            k: v if len(v) > 1 else v[0]
            for k, v in parse_qs(query_string, keep_blank_values=True).items()
        }

    def __iter__(self):
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
        plugin_url: str = '',
        index_route: str = '',
        route_param_name: str = 'action',
    ) -> None:
        """
        Arguments:
            plugin_url str the plugin url in plugin:// notation.
        """
        self.plugin_url = plugin_url or sys.argv[0]
        self.index_route = index_route
        self.route_param_name = route_param_name
        self._routes = {}
        self._error_handlers = {}

    def _find_exception_handler(self, err: Exception):
        for exc_type in type(err).__mro__:
            if exc_type in self._error_handlers:
                return self._error_handlers[exc_type]
        return None

    @staticmethod
    def current_query() -> QueryParams:
        return QueryParams(sys.argv[2])

    @staticmethod
    def current_url() -> str:
        return '%s%s' % (sys.argv[0], sys.argv[2])

    def dispatch(self, qs: t.Optional[str] = None):
        q = self.current_query() if qs is None else QueryParams(qs)
        route_name = q.get_string(self.route_param_name, default=self.index_route)

        if route_name not in self._routes:
            logger.error('Default route not found.')
        else:
            func = self._routes[route_name]
            try:
                func(q=q)
            except Exception as err:
                handler = self._find_exception_handler(err)
                if handler is None:
                    raise
                handler(err, self)

    def register_error_handler(self, exc_type: t.Type[Exception]):
        def decorator(func):
            self._error_handlers[exc_type] = func
            return func
        return decorator

    def route(self, name: str = ''):
        def decorator(func):
            self.register_route(name, func)
            return func
        return decorator

    def register_route(self, name: str, handler: t.Callable[..., None]) -> None:
        self._routes[name or self.index_route] = handler

    def url_for(
        self,
        func_or_name: t.Union[str, t.Callable[..., None]],
        **kwargs,
    ) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            action str
            kwargs dict "argument=value" pairs
        """
        content_type = self.current_query().get_string('content_type')

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

    def url_from_current(self, **kwargs: t.Any) -> str:
        q = QueryParams(sys.argv[2][1:])

        for name, value in kwargs.items():
            q.set(name, value)

        return '%s?%s' % (self.plugin_url, urlencode(dict(q)))
