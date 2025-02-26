from functools import lru_cache
import inspect
import typing as t

from .enums import Scope


__all__ = (
    'get_function_arguments',
    'Parameter',
)


class Parameter(inspect.Parameter):
    class Metadata(t.NamedTuple):
        scope: Scope = Scope.NOTSET
        name: str = ''
        getter: t.Optional[t.Callable[..., t.Any]] = None

    __slots__ = ()

    @lru_cache
    def _get_info(self) -> t.Tuple[t.Any, Metadata]:
        annotation = self.annotation
        metadata = self.Metadata()

        if t.get_origin(annotation) is t.Annotated:
            annotation, *args = t.get_args(annotation)

            for i in args:
                if isinstance(i, Scope):
                    metadata = metadata._replace(scope=i)
                elif isinstance(i, str):
                    metadata = metadata._replace(name=i)
                elif callable(i):
                    metadata = metadata._replace(getter=i)
                else:
                    raise TypeError('Unknown metadata type.')

        if t.get_origin(annotation) is t.Union:
            variants = {i for i in t.get_args(annotation) if not isinstance(None, i)}
            annotation = variants.pop() if len(variants) == 1 else t.Union[tuple(variants)]

        return annotation, metadata

    @property
    def _origin_annotation(self) -> t.Any:
        return self._get_info()[0]

    @property
    def default_value(self) -> t.Any:
        """Returns the default value for use in functions that read data from a query string."""
        return None if self.default is self.empty else self.default

    @property
    def bases(self) -> t.Any:
        """Returns the base type or types to test for in the isinstance and issubclass functions."""
        annotation = self._origin_annotation

        if annotation is self.empty:
            raise TypeError('Missing type annotation.')

        origin = t.get_origin(annotation)

        if inspect.isclass(annotation) or origin is t.Union:
            return annotation

        if issubclass(origin, (t.Sequence, t.Mapping)):
            return origin

        raise TypeError('Unsupported type annotation.')

    @property
    def metadata(self) -> Metadata:
        """Returns the type annotation metadata."""
        return self._get_info()[1]

    @property
    def required(self) -> bool:
        """Returns true if the parameter is required when calling the function, otherwise false."""
        return self.default is self.empty

    @property
    def type_cast(self) -> t.Optional[t.Callable[[str], t.Any]]:
        """Returns a type cast function, or None."""
        metadata = self.metadata

        if metadata.getter is not None:
            return metadata.getter

        annotation = self._origin_annotation

        if annotation is self.empty or not inspect.isclass(annotation):
            return None

        return annotation


@lru_cache
def get_function_arguments(func: t.Callable[..., t.Any]) -> t.Sequence[Parameter]:
    """
    Returns information about the function arguments:
    name, whether required, default value, and annotation.
    """
    sig = inspect.signature(func)
    real_types = t.get_type_hints(func, include_extras=True)
    return [
        Parameter(
            name, param.kind, default=param.default, annotation=real_types.get(name, param.annotation)
        )
        for name, param in sig.parameters.items()
    ]
