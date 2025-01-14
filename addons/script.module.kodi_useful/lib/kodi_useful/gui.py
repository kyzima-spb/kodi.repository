from __future__ import annotations
import typing as t

import xbmc
import xbmcgui


__all__ = (
    'alert',
    'prompt',
    'ListItem',
)


class PromptResult(t.NamedTuple):
    value: t.Any
    canceled: bool = False

    def __bool__(self) -> bool:
        return not self.canceled


def alert(title: str, message: str) -> bool:
    return xbmcgui.Dialog().ok(title, message)


def prompt(
    msg: str,
    required: bool = False,
    default: t.Optional[t.Any] = None,
    type_cast: t.Callable[[str], t.Any] = None,
    hidden: bool = False,
) -> PromptResult:
    """
    Запрашивает данные от пользователя и возвращает ввод.

    Arguments:
        msg (str): строка приглашения.
        required (bool): требуется обязательный ввод, если не указано значение по умолчанию.
        default (mixed): значение, которое будет использовано в случае пустого ввода.
        type_cast (callable): функция обратного вызова для обработки введенного значения.
        input_type (int): внешний вид поля ввода в Kodi.
    """
    if default is not None:
        required = False

    keyboard = xbmc.Keyboard('' if default is None else str(default), msg, hidden)

    while 1:
        keyboard.doModal()

        if not keyboard.isConfirmed():
            return PromptResult(default, True)

        value = keyboard.getText().strip()

        if not value:
            if not required:
                return PromptResult(default)

            alert('Error', 'Input required')
        else:
            if type_cast is None:
                return PromptResult(value)

            try:
                return PromptResult(type_cast(value))
            except ValueError as e:
                alert('Error', str(e))


class ListItem(xbmcgui.ListItem):
    @classmethod
    def next_item(cls, per_page: int, offset: int = 0) -> ListItem:
        label = 'Next page (%d)' % (offset // per_page)
        li = cls(label)
        li.getVideoInfoTag().setPlot(label)
        return li
