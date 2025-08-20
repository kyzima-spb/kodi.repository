from datetime import date, datetime, time
from http.cookiejar import Cookie
import json
import typing as t

from requests.cookies import RequestsCookieJar

from .exceptions import BoostyError
from .enums import MEDIA_TYPE_MAP, Quality


def cookie_jar_to_list(jar: RequestsCookieJar) -> t.List[t.Dict[str, t.Any]]:
    return [
        {k.lstrip('_'): v for k, v in vars(cookie).items()}
        for cookie in jar
    ]


def set_cookies_from_list(jar: RequestsCookieJar, cookies: t.List[t.Dict[str, t.Any]]) -> None:
    for kw in cookies:
        jar.set_cookie(Cookie(**kw))


def extract_content(value: t.Sequence[t.Dict[str, t.Any]]) -> t.Sequence[t.Dict[str, t.Any]]:
    """Extracts content from a list with styles for Boosty."""
    lines = []

    for i in value:
        if i['type'] not in MEDIA_TYPE_MAP and i['content']:
            content_list = json.loads(i.pop('content'))
            content = content_list[0].strip() if content_list else ''

            if content:
                lines.append({'content': content, **i})

    return lines


def extract_images(value: t.Sequence[t.Dict[str, t.Any]]) -> t.Sequence[t.Dict[str, t.Any]]:
    """Extracts images from a list with styles for Boosty."""
    return [i for i in value if i['type'] == 'image']


def extract_text(value: t.Sequence[t.Dict[str, t.Any]]) -> str:
    """Extracts text from a list with styles for Boosty."""
    return '\n\n'.join(i['content'] for i in extract_content(value))


def get_allowed_quality(
    player_urls: t.Sequence[t.Dict[str, t.Any]],
    max_quality: t.Optional[Quality] = None,
    skip_dash: bool = False,
    skip_hls: bool = False,
) -> t.Sequence[t.Tuple[Quality, t.Dict[str, t.Any]]]:
    """Returns available video formats in sorted order from worst to best."""
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

    files = {Quality(u['type']): u for u in player_urls if u['url']}

    return [(q, files[q]) for q in preferred_order if q in files]


def select_best_quality(
    player_urls: t.Sequence[t.Dict[str, t.Any]],
    max_quality: t.Optional[Quality] = None,
    skip_dash: bool = False,
    skip_hls: bool = False,
) -> t.Tuple[Quality, str]:
    """Returns the format name and URL to the video in the best quality."""
    files = get_allowed_quality(player_urls, max_quality, skip_dash=skip_dash, skip_hls=skip_hls)

    if len(files) < 1:
        raise BoostyError('No video streams found.')

    quality, file = files[-1]

    return quality, file['url']


def to_timestamp(dv: t.Optional[date], tv: t.Optional[time]) -> t.Optional[int]:
    if dv is None:
        return None
    return int(datetime.combine(dv, tv).timestamp())
