import requests
import typing as t
import xml.etree.ElementTree as et
from _typeshed import Incomplete
from cache_requests import CachedSession

__all__ = ['parse_html', 'Session']

def parse_html(html: str, tag: str = '', attrs: dict[str, str] | None = None) -> ElementProxy: ...

class ElementProxy:
    _element: Incomplete
    def __init__(self, element: et.Element) -> None: ...
    def __dir__(self): ...
    def __getattr__(self, name): ...
    def findall(self, xpath: str): ...
    def findtext(self, xpath: str, *xpaths: str) -> str: ...
    def first(self, xpath: str, *xpaths: str) -> ElementProxy | None: ...
    @classmethod
    def fromstring(cls, s: str) -> ElementProxy: ...
    def iterfind(self, xpath: str): ...

class Session(CachedSession):
    _base_url: Incomplete
    _global_params: Incomplete
    def __init__(self, base_url: str | None = None, cache: dict[str, t.Any] | None = None, headers: dict[str, t.Any] | None = None, params: dict[str, t.Any] | None = None) -> None: ...
    def download_file(self, url: str, *, chunk_size: int = 65536, no_cache: bool = False, headers: dict[str, t.Any] | None = None, stream: bool = False, translate: bool = False, **kwargs: t.Any) -> str:
        """Downloads a file from the given URL address."""
    def request(self, method: str | bytes, url: str | bytes, *, params: dict[str, t.Any] = None, **kwargs: t.Any) -> requests.Response:
        """
        Выполняет HTTP запрос к серверу.

        В URL адресе можно использовать именованные плейсхолдеры: /user/{user_id},
        а значения для плейсхолдеров передавать в словаре params: {'user_id': 1, 'extended': 1}
        Значения, для которых не заданы плейсхолдеры - будут использованы как параметры строки запроса.
        """
    def parse_html(self, url: str | bytes, tag: str = '', *, attrs: dict[str, str] | None = None, method: str | bytes = 'get', **kwargs: t.Any) -> ElementProxy: ...
