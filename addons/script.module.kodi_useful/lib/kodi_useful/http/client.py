from functools import wraps
import string
import xml.etree.ElementTree as et
import typing as t
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

try:
    import htmlement
except:
    pass

import requests

from ..exceptions import ValidationError


def parse_html(
    html: str,
    tag: str = '',
    attrs: t.Optional[t.Dict[str, str]] = None,
) -> 'ElementProxy':
    parser = htmlement.HTMLement(tag, attrs)
    parser.feed(html)
    return ElementProxy(element=parser.close())


class ElementProxy:
    # __slots__ = ()

    def __init__(self, element: et.Element) -> None:
        self._element = element

    def __dir__(self):
        return dir(self._element)

    def __getattr__(self, name):
        return getattr(self._element, name)

    def findall(self, xpath: str):
        return list(self.iterfind(xpath))

    def findtext(self, xpath: str, *xpaths: str) -> str:
        found = self.first(xpath, *xpaths)
        return '' if found is None else ''.join(found.itertext())

    def first(self, xpath: str, *xpaths: str) -> t.Optional['ElementProxy']:
        for i in (xpath, *xpaths):
            found = self._element.find(i)
            if found is not None:
                return self.__class__(found)
        return None

    @classmethod
    def fromstring(cls, s: str) -> 'ElementProxy':
        return cls(htmlement.fromstring(s))

    def iterfind(self, xpath: str):
        return (self.__class__(i) for i in self._element.iterfind(xpath))


class Session(requests.Session):
    def __init__(
        self,
        base_url: t.Optional[str] = None,
        headers=None,
    ):
        super().__init__()

        self._base_url = base_url

        if headers is not None:
            self.headers.update(headers)

    @wraps(requests.Session.request)
    def request(
        self,
        method: t.Union[str, bytes],
        url: t.Union[str, bytes],
        params: t.Dict[str, t.Any] = None,
        **kwargs: t.Any,
    ) -> requests.Response:
        """
        Выполняет HTTP запрос к серверу.

        В URL адресе можно использовать именованные плейсхолдеры: /user/{user_id},
        а значения для плейсхолдеров передавать в словаре params: {'user_id': 1, 'extended': 1}
        Значения, для которых не заданы плейсхолдеры - будут использованы как параметры строки запроса.
        """
        if bool(urlparse(url).netloc):
            return super().request(method, url, **kwargs)

        if self._base_url is not None:
            url = '%s/%s' % (self._base_url.rstrip('/'), url.lstrip('/'))

        if params is not None:
            formatter = string.Formatter()

            url = url.format(**{
                field_name: params.pop(field_name)
                for _, field_name, _, _ in formatter.parse(url)
                if field_name
            })

        return super().request(method, url, params=params, **kwargs)

    def parse_html(
        self,
        url: t.Union[str, bytes],
        tag: str = '',
        *,
        attrs: t.Optional[t.Dict[str, str]] = None,
        method: t.Union[str, bytes] = 'get',
        **kwargs: t.Any,
    ) -> 'ElementProxy':
        response = self.request(method, url, **kwargs)

        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            raise ValidationError('%s for url: %s' % (response.reason, response.url)) from err

        return parse_html(response.text, tag, attrs)
