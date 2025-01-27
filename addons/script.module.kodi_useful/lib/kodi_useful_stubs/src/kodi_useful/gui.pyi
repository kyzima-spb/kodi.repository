import typing as t
import xbmcgui

__all__ = ['alert', 'prompt', 'ListItem']

class PromptResult(t.NamedTuple):
    value: t.Any
    canceled: bool = ...
    def __bool__(self) -> bool: ...

def alert(title: str, message: str) -> bool: ...
def prompt(msg: str, required: bool = False, default: t.Any | None = None, type_cast: t.Callable[[str], t.Any] = None, hidden: bool = False) -> PromptResult:
    """
    Запрашивает данные от пользователя и возвращает ввод.

    Arguments:
        msg (str): строка приглашения.
        required (bool): требуется обязательный ввод, если не указано значение по умолчанию.
        default (mixed): значение, которое будет использовано в случае пустого ввода.
        type_cast (callable): функция обратного вызова для обработки введенного значения.
        input_type (int): внешний вид поля ввода в Kodi.
    """

class ListItem(xbmcgui.ListItem):
    @classmethod
    def next_item(cls, per_page: int, offset: int = 0) -> ListItem: ...
