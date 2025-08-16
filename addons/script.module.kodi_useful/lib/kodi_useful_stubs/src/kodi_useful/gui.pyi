import typing as t
import xbmcgui
from .core import Addon
from .enums import Content
from _typeshed import Incomplete
from functools import cached_property

__all__ = ['alert', 'confirm', 'create_next_element', 'create_next_item', 'notification', 'prompt', 'select', 'Directory']

_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])

class PromptResult(t.NamedTuple):
    value: t.Any
    canceled: bool = ...
    def __bool__(self) -> bool: ...

def alert(title: str, message: str, localize_args: tuple[t.Any, ...] = (), localize_kwargs: dict[str, t.Any] | None = None) -> bool: ...
def confirm(title: str, message: str, nolabel: str = '', yeslabel: str = '', autoclose: int = 0, defaultbutton: int = ..., localize_args: tuple[t.Any, ...] = (), localize_kwargs: dict[str, t.Any] | None = None) -> bool: ...
def notification(title: str, message: str, icon: str = '', show_time: int = 0, sound: bool = True, localize_args: tuple[t.Any, ...] = (), localize_kwargs: dict[str, t.Any] | None = None) -> None: ...
def select(title: str, choices: list[str | xbmcgui.ListItem], autoclose: int = 0, preselect: int = -1, use_details: bool = False, localize_args: tuple[t.Any, ...] = (), localize_kwargs: dict[str, t.Any] | None = None) -> int: ...
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
def create_next_item(url): ...
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
    _cache_to_disk: Incomplete
    content: Incomplete
    content_type: Incomplete
    sort_methods: Incomplete
    _title: Incomplete
    _ltitle: Incomplete
    def __init__(self, addon: Addon | None = None, cache_to_disk: bool = True, content: Content = ..., content_type: str | None = None, sort_methods: t.Sequence[int | tuple[int, str, str]] = (), title: str = '', ltitle: int | str = '') -> None: ...
    @property
    def addon(self) -> Addon: ...
    @property
    def cache_to_disk(self) -> bool: ...
    @cached_property
    def title(self) -> str: ...
    def __call__(self, func: _F) -> _F: ...
