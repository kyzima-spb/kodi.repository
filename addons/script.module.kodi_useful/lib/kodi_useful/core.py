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


class Router:
    def __init__(
        self,
        plugin_url: str,
        index_route: str = '',
        route_param_name: str = 'action',
    ) -> None:
        """
        Arguments:
            plugin_url str the plugin url in plugin:// notation.
        """
        self.plugin_url = plugin_url
        self.index_route = index_route
        self.route_param_name = route_param_name
        self.routes = {}

    def dispatch(self, qs: str):
        q = QueryParams(qs.strip('?'))
        route_name = q.get_string(self.route_param_name, default=self.index_route)

        if route_name not in self.routes:
            logger.error('Default route not found.')
        else:
            func = self.routes[route_name]
            func(q=q)

    def route(self, name: str = ''):
        def decorator(func):
            self.register_route(name, func)
            return func
        return decorator

    def register_route(self, name: str, handler: t.Callable[..., None]) -> None:
        self.routes[name or self.index_route] = handler

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
        if callable(func_or_name):
            for name, func in self.routes.items():
                if func is func_or_name:
                    kwargs[self.route_param_name] = name
                    break
            else:
                raise RuntimeError('The passed argument func is not a route handler.')
        else:
            if func_or_name not in self.routes:
                raise RuntimeError('The passed argument is not a route name.')
            kwargs[self.route_param_name] = func_or_name

        return '%s?%s' % (self.plugin_url, urlencode(kwargs))

    # def next_url(
    #     self,
    #     func_or_name: t.Union[str, t.Callable[..., None]],
    #     offset: int = 0,
    # ) -> str:
    #     limit = 25
    #     return self.url_for(func_or_name, offset=offset + limit)
