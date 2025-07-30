from http.cookiejar import Cookie
import typing as t

from requests.cookies import RequestsCookieJar


def cookie_jar_to_list(jar: RequestsCookieJar) -> t.List[t.Dict[str, t.Any]]:
    return [
        {k.lstrip('_'): v for k, v in vars(cookie).items()}
        for cookie in jar
    ]


def set_cookies_from_list(jar: RequestsCookieJar, cookies: t.List[t.Dict[str, t.Any]]) -> None:
    for kw in cookies:
        jar.set_cookie(Cookie(**kw))
