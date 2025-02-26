import typing as t
import xbmcgui
from .core import Addon
from .enums import Content
from _typeshed import Incomplete
from functools import cached_property

__all__ = ['alert', 'create_next_element', 'prompt', 'Directory']

_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])

class PromptResult(t.NamedTuple):
    value: t.Any
    canceled: bool = ...
    def __bool__(self) -> bool: ...

def alert(title: str, message: str) -> bool: ...
def create_next_element(func_or_name: str | t.Callable[..., None], items_per_page: int | None = None, limit_name: str = 'items_per_page', offset: int | None = None, offset_name: str = 'offset', **kwargs: t.Any) -> tuple[str, xbmcgui.ListItem, bool]:
    """
    Arguments:
        func_or_name (str|Callable):
            A reference to the handler function or a string to import it.
        items_per_page (int):
            The number of items per page.
        limit_name (str):
            The name of the setting parameter that specifies the number of items per page.
        offset (int):
            Offset relative to the first element of the page.
        offset_name (str):
            The name of the URL parameter that specifies the offset.
        kwargs (dict):
            Query string parameters.
    """
def prompt(msg: str, required: bool = False, default: t.Any | None = None, type_cast: t.Callable[[str], t.Any] = None, hidden: bool = False) -> PromptResult:
    """
    Запрашивает данные от пользователя и возвращает ввод.

    Arguments:
        msg (str): Строка приглашения.
        required (bool): Требуется обязательный ввод, если не указано значение по умолчанию.
        default (mixed): Значение, которое будет использовано в случае пустого ввода.
        type_cast (callable): Функция обратного вызова для обработки введенного значения.
        input_type (int): Внешний вид поля ввода в Kodi.
    """

class Directory:
    content_type_map: Incomplete
    _addon: Incomplete
    cache_to_disk: Incomplete
    content: Incomplete
    content_type: Incomplete
    sort_methods: Incomplete
    _title: Incomplete
    _ltitle: Incomplete
    def __init__(self, addon: Addon | None = None, cache_to_disk: bool = True, content: Content = ..., content_type: str | None = None, sort_methods: t.Sequence[int | tuple[int, str, str]] = (), title: str = '', ltitle: int | str = '') -> None: ...
    @property
    def addon(self) -> Addon: ...
    @cached_property
    def title(self) -> str: ...
    def __call__(self, func: _F) -> _F: ...
