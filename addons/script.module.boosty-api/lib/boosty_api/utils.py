from http.cookiejar import Cookie
from itertools import filterfalse
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


def select_best_quality(
    player_urls: t.Sequence[t.Dict[str, t.Any]],
    preferred_order: t.Tuple[Quality, ...] = (
        Quality.DASH,
        Quality.HLS,
        Quality.FHD,
        Quality.HD,
        Quality.SD_480,
        Quality.SD_360,
        Quality.SD_240,
        Quality.SD_144,
    ),
    skip_dash: bool = False,
    skip_hls: bool = False,
) -> t.Tuple[Quality, str]:
    """Returns the format name and URL to the video in the best quality."""
    files = {Quality(u['type']): u['url'] for u in player_urls if u['url']}

    for fmt in filterfalse(
        lambda f: (skip_dash and f == Quality.DASH) or (skip_hls and f == Quality.HLS),
        preferred_order
    ):
        if fmt in files:
            return fmt, files[fmt]

        raise BoostyError('No video streams found.')
