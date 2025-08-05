from datetime import date, datetime, time
from http.cookiejar import Cookie
import json
import typing as t

from requests.cookies import RequestsCookieJar

from .exceptions import BoostyError
from .enums import Quality


def cookie_jar_to_list(jar: RequestsCookieJar) -> t.List[t.Dict[str, t.Any]]:
    return [
        {k.lstrip('_'): v for k, v in vars(cookie).items()}
        for cookie in jar
    ]


def set_cookies_from_list(jar: RequestsCookieJar, cookies: t.List[t.Dict[str, t.Any]]) -> None:
    for kw in cookies:
        jar.set_cookie(Cookie(**kw))


def extract_images(value: t.Sequence[t.Dict[str, t.Any]]) -> t.Sequence[t.Dict[str, t.Any]]:
    """Extracts images from a list with styles for Boosty."""
    return [i for i in value if i['type'] == 'image']


def extract_text(value: t.Sequence[t.Dict[str, t.Any]]) -> str:
    """Extracts text from a list with styles for Boosty."""
    lines = [
        json.loads(i['content'])
        for i in value
        if i['type'] == 'text' and i['content']
    ]
    return '\n\n'.join(i[0].strip() for i in lines if i[0])


def select_best_quality(
    player_urls: t.Sequence[t.Dict[str, t.Any]],
    max_quality: t.Optional[Quality] = None,
    skip_dash: bool = False,
    skip_hls: bool = False,
) -> t.Tuple[Quality, str]:
    """Returns the format name and URL to the video in the best quality."""
    preferred_order = [
        Quality.SD_144,
        Quality.SD_240,
        Quality.SD_360,
        Quality.SD_480,
        Quality.HD,
        Quality.FHD,
        Quality.QHD,
        Quality.UHD,
    ]

    if max_quality is not None:
        stop_index = preferred_order.index(max_quality.value) + 1
        preferred_order = preferred_order[:stop_index]

    if not skip_hls:
        preferred_order.append(Quality.HLS)

    if not skip_dash:
        preferred_order.append(Quality.DASH)

    files = {Quality(u['type']): u['url'] for u in player_urls if u['url']}

    for fmt in reversed(preferred_order):
        if fmt in files:
            return fmt, files[fmt]

    raise BoostyError('No video streams found.')


def to_timestamp(dv: t.Optional[date], tv: t.Optional[time]) -> t.Optional[int]:
    if dv is None:
        return None
    return int(datetime.combine(dv, tv).timestamp())
