from functools import lru_cache
import typing as t
from urllib.parse import parse_qs, urlencode

from .enums import Scope
from .exceptions import RouterError
from .introspection import get_function_arguments, Parameter
from .utils import cast_bool

if t.TYPE_CHECKING:
    from .core import Addon


__all__ = (
    'router',
    'QueryParams',
    'Router',
)


_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])
_T = t.TypeVar('_T')


class QueryParams:
    def __init__(self, query_string: str) -> None:
        query_string = query_string.strip('?')
        self._params = parse_qs(query_string, keep_blank_values=True)

    # @t.overload
    # def get(self, name: str) -> t.Optional[t.Any]: ...
    #
    # @t.overload
    # def get(self, name: str, default: _T) -> t.Optional[_T]: ...

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
        return self.get(name, default=default, type_cast=cast_bool)

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


class Route(t.NamedTuple):
    name: str
    handler: t.Callable[..., None]

    @property
    @lru_cache
    def arguments(self) -> t.Sequence[Parameter]:
        return get_function_arguments(self.handler)


class Router:
    def __init__(
        self,
        route_param_name: str = 'r',
    ) -> None:
        """
        Arguments:
            route_param_name (str):
                The name of the query string parameter to specify the route name.
        """
        self._routes: t.Dict[str, Route] = {}
        self._error_handlers: t.Dict[t.Type[Exception], t.Callable[..., None]] = {}
        self.route_param_name = route_param_name

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
            raise err

    def dispatch(self, addon: 'Addon', query: QueryParams) -> None:
        """
        Processes a request.

        Arguments:
            addon (Addon): The object of the current plugin.
            query (str): Query string.
        """
        route_name = query.get(self.route_param_name, default='')
        route = self.find_route(route_name)
        handler_kwargs = {}

        for p in route.arguments:
            if isinstance(addon, p.bases):
                handler_kwargs[p.name] = addon
            elif p.metadata.scope != Scope.NOTSET:
                name = p.metadata.name or p.name
                scope = p.metadata.scope

                if scope == Scope.QUERY:
                    handler_kwargs[p.name] = query.get(
                        name,
                        required=p.required,
                        default=p.default_value,
                        type_cast=p.type_cast,
                    )
                elif scope == Scope.SETTINGS:
                    handler_kwargs[p.name] = addon.get_setting(name, p.type_cast or str)

        try:
            return route.handler(**handler_kwargs)
        except Exception as err:
            return self._handle_exception(err)

    def find_route(self, func_or_name: t.Union[str, t.Callable[..., None]]) -> Route:
        """
        Returns the route object for the passed handler.

        Arguments:
            func_or_name (str|Callable):
                A reference to the handler function or a string to import it.
        """
        if callable(func_or_name):
            name = self._get_route_name(func_or_name)
            route = self._routes.get(name)

            if route is None or route.handler is not func_or_name:
                raise RouterError(f'The passed argument {func_or_name!r} is not a route handler.')

            return route

        if func_or_name not in self._routes:
            raise RouterError(f'The passed argument {func_or_name!r} is not a route name.')

        return self._routes[func_or_name]

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
        name = self._get_route_name(handler)

        if name in self._routes:
            raise RouterError(f'Duplicate route name {name!r}')

        self._routes[name] = Route(name=name, handler=handler)

        if is_root:
            self._routes[''] = self._routes[name]

    def route(
        self,
        func_or_none: t.Optional[_F] = None,
        is_root: bool = False,
    ) -> t.Callable[[_F], _F]:
        """
        Adds a handler for the page.

        Arguments:
            func_or_none (callable): Handler function.
            is_root (bool): This is the root page.
        """

        def decorator(func: _F) -> _F:
            self.register_route(func, is_root=is_root)
            return func

        if func_or_none is not None:
            return decorator(func_or_none)

        return decorator

    def url_for(
        self,
        func_or_name: t.Union[str, t.Callable[..., None]],
        base_url: str = '',
        **kwargs: t.Any,
    ) -> str:
        """
        Returns a URL for calling the plugin from the given set of keyword arguments.

        Arguments:
            func_or_name (str|Callable):
                A reference to the handler function or a string to import it.
            base_url (str):
                The base URL for all returned URLs.
            kwargs (dict): Query string parameters.
        """
        route = self.find_route(func_or_name)
        kwargs[self.route_param_name] = route.name

        for p in route.arguments:
            if p.metadata.scope == Scope.QUERY and p.required and p.name not in kwargs:
                raise ValueError(f'Missing value for required parameter {p.name!r} in query string.')

        return '%s?%s' % (base_url, urlencode(kwargs))


router = Router()
