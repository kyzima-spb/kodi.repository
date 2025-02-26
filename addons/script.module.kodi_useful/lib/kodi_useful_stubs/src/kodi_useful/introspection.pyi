import inspect
import typing as t
from .enums import Scope
from _typeshed import Incomplete

__all__ = ['get_function_arguments', 'Parameter']

class Parameter(inspect.Parameter):
    class Metadata(t.NamedTuple):
        scope: Scope = ...
        name: str = ...
        getter: t.Callable[..., t.Any] | None = ...
    __slots__: Incomplete
    def _get_info(self) -> tuple[t.Any, Metadata]: ...
    @property
    def _origin_annotation(self) -> t.Any: ...
    @property
    def default_value(self) -> t.Any:
        """Returns the default value for use in functions that read data from a query string."""
    @property
    def bases(self) -> t.Any:
        """Returns the base type or types to test for in the isinstance and issubclass functions."""
    @property
    def metadata(self) -> Metadata:
        """Returns the type annotation metadata."""
    @property
    def required(self) -> bool:
        """Returns true if the parameter is required when calling the function, otherwise false."""
    @property
    def type_cast(self) -> t.Callable[[str], t.Any] | None:
        """Returns a type cast function, or None."""

def get_function_arguments(func: t.Callable[..., t.Any]) -> t.Sequence[Parameter]:
    """
    Returns information about the function arguments:
    name, whether required, default value, and annotation.
    """
