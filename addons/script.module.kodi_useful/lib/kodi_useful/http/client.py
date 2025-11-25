import hashlib
import mimetypes
import os
import string
import xml.etree.ElementTree as et
import typing as t
from urllib.parse import urlparse

try:
    import htmlement
except:
    pass

import requests
from cache_requests import CachedSession

from .utils import get_content_disposition, split_pairs
from ..core import current_addon
from ..exceptions import ValidationError


__all__ = (
    'parse_html',
    'Session',
)


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


class Session(CachedSession):
    def __init__(
        self,
        base_url: t.Optional[str] = None,
        cache: t.Optional[t.Dict[str, t.Any]] = None,
        headers: t.Optional[t.Dict[str, t.Any]] = None,
        params: t.Optional[t.Dict[str, t.Any]] = None,
    ):
        cache_kwargs = cache or {}
        cache_kwargs.setdefault('cache_name', current_addon.get_data_path('requests', 'http_cache'))
        cache_kwargs.setdefault('expire_after', 0)

        super().__init__(**cache_kwargs)

        self._base_url = base_url
        self._global_params = params

        if headers is not None:
            self.headers.update(headers)

    def download_file(
        self,
        url: str,
        *,
        chunk_size: int = 65536,
        no_cache: bool = False,
        headers: t.Optional[t.Dict[str, t.Any]] = None,
        stream: bool = False,
        translate: bool = False,
        **kwargs: t.Any,
    ) -> str:
        """Downloads a file from the given URL address."""
        response = self.head(url, expire_after=0, headers=headers, **kwargs)

        if 'Content-Disposition' in response.headers:
            _, ext = os.path.splitext(
                get_content_disposition(response.headers['Content-Disposition'])
            )
        elif 'Content-Type' in response.headers:
            ext = mimetypes.guess_extension(response.headers['Content-Type'])
        else:
            ext = ''

        lookup = ['requests', 'downloads', *split_pairs(hashlib.sha256(url.encode('utf-8')).hexdigest())]
        lookup[-1] += ext
        path = current_addon.get_data_path(*lookup)

        if no_cache or not os.path.exists(path) or response.headers.get('Content-Length', 0) != os.stat(path).st_size:
            response = self.get(url, stream=stream, expire_after=0, headers=headers, **kwargs)

            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size):
                    f.write(chunk)

        return current_addon.get_data_path(*lookup, translate=translate)

    def request(
        self,
        method: t.Union[str, bytes],
        url: t.Union[str, bytes],
        *,
        params: t.Dict[str, t.Any] = None,
        **kwargs: t.Any,
    ) -> requests.Response:
        """
        Выполняет HTTP запрос к серверу.

        В URL адресе можно использовать именованные плейсхолдеры: /user/{user_id},
        а значения для плейсхолдеров передавать в словаре params: {'user_id': 1, 'extended': 1}
        Значения, для которых не заданы плейсхолдеры - будут использованы как параметры строки запроса.
        """
        if not urlparse(url).netloc and self._base_url is not None:
            url = '%s/%s' % (self._base_url.rstrip('/'), url.lstrip('/'))

        if self._global_params and params:
            params = {**self._global_params, **params}
        else:
            params = params or self._global_params

        if params is not None:
            formatter = string.Formatter()

            url = url.format(**{
                field_name: params.pop(field_name)
                for _, field_name, _, _ in formatter.parse(url)
                if field_name
            })

        response = super().request(method, url, params=params, **kwargs)
        response.raise_for_status()

        return response

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
