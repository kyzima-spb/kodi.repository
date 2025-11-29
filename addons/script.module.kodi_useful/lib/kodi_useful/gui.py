from functools import wraps, cached_property
import typing as t

import xbmc
import xbmcgui
import xbmcplugin

from .core import current_addon, Addon
from .enums import Content


__all__ = (
    'alert',
    'confirm',
    'create_next_element',
    'create_next_item',
    'notification',
    'prompt',
    'select',
    'Directory',
)


_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])


def _localize(
    string_id: t.Union[str, int],
    localize_args: t.Tuple[t.Any, ...] = (),
    localize_kwargs: t.Optional[t.Dict[str, t.Any]] = None,
) -> str:
    """Returns the translation for the passed identifier."""
    localize_kwargs = localize_kwargs or {}
    return current_addon.localize(string_id, *localize_args, **localize_kwargs)


class PromptResult(t.NamedTuple):
    value: t.Any
    canceled: bool = False

    def __bool__(self) -> bool:
        return not self.canceled


def alert(
    title: str,
    message: str,
    localize_args: t.Tuple[t.Any, ...] = (),
    localize_kwargs: t.Optional[t.Dict[str, t.Any]] = None,
) -> bool:
    return xbmcgui.Dialog().ok(
        _localize(title, localize_args, localize_kwargs),
        _localize(message, localize_args, localize_kwargs),
    )


def confirm(
    title: str,
    message: str,
    nolabel: str = '',
    yeslabel: str = '',
    autoclose: int = 0,
    defaultbutton: int = xbmcgui.DLG_YESNO_NO_BTN,
    localize_args: t.Tuple[t.Any, ...] = (),
    localize_kwargs: t.Optional[t.Dict[str, t.Any]] = None,
) -> bool:
    return xbmcgui.Dialog().yesno(
        _localize(title, localize_args, localize_kwargs),
        _localize(message, localize_args, localize_kwargs),
        _localize(nolabel, localize_args, localize_kwargs),
        _localize(yeslabel, localize_args, localize_kwargs),
        autoclose,
        defaultbutton,
    )


def notification(
    title: str,
    message: str,
    icon: str = '',
    show_time: int = 0,
    sound: bool = True,
    localize_args: t.Tuple[t.Any, ...] = (),
    localize_kwargs: t.Optional[t.Dict[str, t.Any]] = None,
) -> None:
    xbmcgui.Dialog().notification(
        _localize(title, localize_args, localize_kwargs),
        _localize(message, localize_args, localize_kwargs),
        icon,
        show_time,
        sound,
    )


def select(
    title: str,
    choices: t.List[t.Union[str, xbmcgui.ListItem]],
    autoclose: int = 0,
    preselect: int = -1,
    use_details: bool = False,
    localize_args: t.Tuple[t.Any, ...] = (),
    localize_kwargs: t.Optional[t.Dict[str, t.Any]] = None,
) -> int:
    return xbmcgui.Dialog().select(
        _localize(title, localize_args, localize_kwargs),
        choices,
        autoclose,
        preselect,
        use_details,
    )


def create_next_element(
    func_or_name: t.Union[str, t.Callable[..., None]],
    items_per_page: t.Optional[int] = None,
    limit_name: str = 'items_per_page',
    offset: t.Optional[int] = None,
    offset_name: str = 'offset',
    **kwargs: t.Any,
) -> t.Tuple[str, xbmcgui.ListItem, bool]:
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
    current_addon = Addon.get_instance()

    if items_per_page is None:
        items_per_page = current_addon.get_setting(limit_name, int)

    if offset is None:
        offset = current_addon.query.get_int(offset_name, items_per_page)

    label = current_addon.localize('Next page (%d)', (offset // items_per_page) + 1)
    item = xbmcgui.ListItem(label)
    item.getVideoInfoTag().setPlot(label)

    handler_kwargs = current_addon.query.to_dict()
    handler_kwargs.update(kwargs)
    handler_kwargs[offset_name] = offset
    current_addon.logger.debug(f'Next url kwargs {handler_kwargs}')
    url = current_addon.url_for(func_or_name, **handler_kwargs)

    return url, item, True


def create_next_item(url):
    current_addon = Addon.get_instance()

    label = current_addon.localize('Next page')
    item = xbmcgui.ListItem(label)
    item.getVideoInfoTag().setPlot(label)

    return url, item, True


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
        msg (str): Строка приглашения.
        required (bool): Требуется обязательный ввод, если не указано значение по умолчанию.
        default (mixed): Значение, которое будет использовано в случае пустого ввода.
        type_cast (callable): Функция обратного вызова для обработки введенного значения.
        input_type (int): Внешний вид поля ввода в Kodi.
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


class Directory:
    content_type_map = {
        Content.FILES: '',
        Content.ARTISTS: '',
        Content.ALBUMS: '',
        Content.GAMES: '',
        Content.EPISODES: 'video',
        Content.IMAGES: 'image',
        Content.MOVIES: 'video',
        Content.MUSICVIDEOS: 'video',
        Content.SONGS: 'audio',
        Content.TVSHOWS: 'video',
        Content.VIDEOS: 'video',
    }

    def __init__(
        self,
        addon: t.Optional[Addon] = None,
        cache_to_disk: t.Optional[bool] = None,
        content: Content = Content.FILES,
        content_type: t.Optional[str] = None,
        sort_methods: t.Sequence[t.Union[int, t.Tuple[int, str, str]]] = (),
        ltitle: t.Union[int, str] = '',
        title: str = '',
    ) -> None:
        self.addon = addon = addon or current_addon
        self.cache_to_disk = not addon.debug if cache_to_disk is None else cache_to_disk
        self.content = content
        self.content_type = content_type or self.content_type_map.get(content, '')
        self.sort_methods = [(i, '', '') if isinstance(i, int) else i for i in sort_methods]

        self._ltitle = ltitle
        self._title = title

    @cached_property
    def title(self) -> str:
        title = self.addon.query.get('title', default=self._title)

        if not title and self._ltitle:
            title = self.addon.localize(self._ltitle)

        if not title:
            title = self.content.title()

        return title

    def __call__(self, func: _F) -> _F:
        @wraps(func)
        def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
            xbmcplugin.setPluginCategory(self.addon.handle, self.title)
            xbmcplugin.setContent(self.addon.handle, self.content)

            items = func(*args, **kwargs)
            # self.addon.logger.error(f'List directory {items}')

            if items is None:
                xbmcplugin.endOfDirectory(self.addon.handle, succeeded=False)
                return False

            xbmcplugin.addDirectoryItems(self.addon.handle, list(items))

            for method, label_mask, label2_mask in self.sort_methods:
                xbmcplugin.addSortMethod(self.addon.handle, method, label_mask, label2_mask)

            xbmcplugin.endOfDirectory(self.addon.handle, cacheToDisc=self.cache_to_disk)

            return True
        return t.cast(_F, wrapper)
