from datetime import date
from functools import partial
from http import HTTPStatus
import logging
import json
import re
import threading
import time
import typing as t

import requests
from requests.adapters import HTTPAdapter

from .enums import MediaType
from .exceptions import AuthError, BoostyError, BoostyApiError, LoginRequired
from .models import BasePost, Collection, Filter, Media, Post
from .utils import cookie_jar_to_list, set_cookies_from_list


__all__ = (
    'BoostyApi',
)


DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'


class Credentials:
    def __init__(self, credentials_filename: str) -> None:
        self._filename = credentials_filename
        self._data = self._load_from_file()

    @property
    def client_id(self) -> t.Optional[str]:
        for cookie in self.cookies:
            if cookie['name'] == '_clientId':
                return cookie['value']
        return None

    @property
    def cookies(self) -> t.List[t.Dict[str, t.Any]]:
        return self._data.setdefault('cookies', [])

    @property
    def token(self) -> t.Optional[t.Dict[str, t.Any]]:
        return self._data.get('token')

    @token.setter
    def token(self, token_dict: t.Optional[t.Dict[str, t.Any]]) -> None:
        if token_dict is not None:
            token_dict['expires_at'] = time.time() + token_dict.pop('expires_in')
        self._data['token'] = token_dict

    def _load_from_file(self) -> t.Dict[str, t.Any]:
        try:
            with open(self._filename) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self) -> None:
        with open(self._filename, 'w') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


class BoostyApi:
    RPS_DELAY = 0.34

    def __init__(
        self,
        user_input_handler: t.Optional[t.Callable[..., str]] = None,
        login: t.Optional[str] = None,
        credentials_filename: str = 'boosty-credentials.json',
        api_url: str = 'https://api.boosty.to',
        version: str = '1',
        user_agent: str = DEFAULT_USER_AGENT,
        debug: bool = False,
    ) -> None:
        self._user_input_handler = user_input_handler
        self._credentials = Credentials(credentials_filename)

        self._lock = threading.Lock()
        self._last_request: float = 0
        self.logger = logging.getLogger('boosty_api')

        self.api_url = api_url.rstrip('/')
        self.api_version = version.lstrip('v')
        self.user_agent = user_agent
        self.login = login
        self.session = self._get_session()

        self.get_media = partial(get_media, self)
        self.get_media_by_id = partial(get_media_by_id, self)
        self.get_post = partial(get_post, self)
        self.get_posts = partial(get_posts, self)
        self.get_profile = partial(get_profile, self)
        self.get_profile_by_url = partial(get_profile_by_url, self)
        self.get_subscriptions = partial(get_subscriptions, self)

        if debug:
            self.enable_debug()

    def __repr__(self) -> str:
        args = ', '.join((
            f'user_input_handler={self._user_input_handler!r}',
            f'login={self.login!r}',
            f'credentials_filename={self._credentials._filename!r}',
            f'api_url={self.api_url!r}',
            f'version={self.api_version!r}',
            f'user_agent={self.user_agent!r}',
        ))
        return f'{type(self).__name__}({args})'

    def enable_debug(self) -> None:
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())

        class DebugAdapter(HTTPAdapter):
            def send(self, request: requests.PreparedRequest, **kwargs: t.Any) -> requests.Response:  # type: ignore[override]
                response = super().send(request, **kwargs)

                print('{request.method} {response.status_code} {request.url} {response.history}'.format(
                    request=request, response=response
                ))
                print('{request.headers!r}\n{request.body!r}'.format(request=request))

                if not response.ok:
                    print(response.text)

                return response

        self.session.mount('http://', DebugAdapter())
        self.session.mount('https://', DebugAdapter())

    @property
    def active_sessions(self) -> t.Sequence[t.Dict[str, t.Any]]:
        return self.request('get', '/user/session/')['data']['sessions']

    @active_sessions.deleter
    def active_sessions(self) -> None:
        self.request('delete', '/user/session/')

    @property
    def current_user(self) -> t.Optional[t.Dict[str, t.Any]]:
        """Returns the current user if the current session is authenticated."""
        if self._credentials.token is None:
            return None
        return self.request('get', '/user/current')

    @property
    def default_currency(self) -> str:
        """Returns the default currency for the current session."""
        return self.request('get', '/payment/default_currency', skip_auth=True)['defaultCurrency']

    def _get_session(self) -> requests.Session:
        """Returns a session for working with HTTP requests."""
        session = requests.Session()
        session.headers.update({
            'accept': 'application/json, text/plain, */*',
            'accept-Language': 'ru-RU,ru;q=0.5',
            'cache-Control': 'no-cache',
            'origin': 'https://boosty.to',
            'pragma': 'no-cache',
            'referer': 'https://boosty.to/',
            'user-agent': self.user_agent,
        })

        if self._credentials.client_id is None:
            self._credentials.cookies.extend(
                cookie_jar_to_list(session.get('https://boosty.to/').cookies)
            )

            if self._credentials.client_id is None:
                raise BoostyError('Failed to obtain _clientId from cookies')

            self._credentials.save()

        set_cookies_from_list(session.cookies, self._credentials.cookies)
        session.headers.update({
            'x-app': 'web',
            'x-from-id': self._credentials.client_id,
            'x-locale': 'en_US',
            'x-referer': '',
        })

        return session

    def _parse_response_or_raise(
        self,
        response: requests.Response,
        exc_type: t.Type[BoostyError],
        kwargs: t.Optional[t.Any] = None,
    ) -> t.Dict[str, t.Any]:
        kwargs = kwargs or {}

        try:
            response_dict = response.json()
        except json.JSONDecodeError:
            raise exc_type('Invalid JSON response', **kwargs)

        if not response.ok:
            raise exc_type(response_dict, **kwargs)

        return response_dict

    def _pass_confirmation_code(self) -> str:
        """Returns the code from the SMS entered by the user."""
        if self._user_input_handler is None:
            raise AuthError('No user input handler specified.')
        return self._user_input_handler()

    def _get_token_by_code(self, login: str, code: str, sms_code: str) -> t.Dict[str, t.Any]:
        """Returns an access token in exchange for a code."""
        response = self.session.put(f'{self.api_url}/auth/phone/verification_code/confirm', data={
           'phone': login,
           'code': code,
           'sms_code': sms_code,
           'device_os': 'web',
           'device_id': self._credentials.client_id,
        })
        return self._parse_response_or_raise(response, exc_type=AuthError)

    def _get_token_by_refresh(self, refresh_token: str) -> t.Dict[str, t.Any]:
        """Returns an access token in exchange for a refresh token."""
        response = self.session.post(f'{self.api_url}/oauth/token/', data={
            'device_id': self._credentials.client_id,
            'device_os': 'web',
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        })
        return self._parse_response_or_raise(response, exc_type=AuthError)

    def _send_sms_code(self, phone: str) -> str:
        """Sends an SMS confirmation code and returns a service response."""
        response = self.session.post(f'{self.api_url}/auth/phone/verification_code/send', data={
            'device_id': self._credentials.client_id,
            'device_os': 'web',
            'phone': phone,
        })
        response_dict = self._parse_response_or_raise(response, exc_type=AuthError)
        return response_dict['data']['phoneCode']['code']

    def _update_access_token(self, force: bool = False) -> bool:
        """Refreshes the access token using the refresh token."""
        token = self._credentials.token

        if token is None:
            self.logger.warning('Token not found, falling back to interactive auth.')
            return False

        if not force and time.time() < token['expires_at']:
            return True

        try:
            self._credentials.token = self._get_token_by_refresh(token['refresh_token'])
            self._credentials.save()
            return True
        except AuthError as err:
            self.logger.warning('Refresh token failed, falling back to interactive auth: %s.', str(err))
            return False

    def auth(self, force: bool = False) -> None:
        """Starts the user authentication process."""
        if self._update_access_token(force=force):
            return None

        if not self.login:
            raise LoginRequired('Login is required to auth')

        code = self._send_sms_code(self.login)
        succeeded = False

        while not succeeded:
            try:
                sms_code = self._pass_confirmation_code()
                self._credentials.token = self._get_token_by_code(self.login, code, sms_code)
                self._credentials.save()
                succeeded = True
            except AuthError as err:
                if err.error_code not in {'invalid_sms_code', 'invalid_param'}:
                    raise

    def logout(self) -> None:
        """Exits the current session."""
        if self._credentials.token is None:
            return None

        response = self.session.delete(f'{self.api_url}/oauth/token', params={
            'access_token': self._credentials.token['access_token'],
            'device_id': self._credentials.client_id,
            'device_os': 'web',
        })
        self._parse_response_or_raise(response, exc_type=AuthError)

        self._credentials.token = None
        self._credentials.save()

    def request(self, method: str, path: str, skip_auth: bool = False, **kwargs: t.Any) -> t.Any:
        url = f'{self.api_url}/v{self.api_version}/{path.lstrip("/")}'

        if not skip_auth and self._credentials.token:
            headers = kwargs.setdefault('headers', {})
            headers['authorization'] = 'Bearer %s' % self._credentials.token['access_token']

        with self._lock:
            delay = self.RPS_DELAY - (time.time() - self._last_request)

            if delay > 0:
                time.sleep(delay)

            response = self.session.request(method, url, **kwargs)
            self._last_request = time.time()

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            self.logger.info('Unauthorized. Attempting to re-authenticate.')
            self.auth(force=True)
            return self.request(method, path, **kwargs)

        return self._parse_response_or_raise(response, BoostyApiError, {
            'boosty': self,
            'response': response,
            'request_kwargs': {'method': method, 'path': path, **kwargs},
        })


def resolve_username(boosty_session: BoostyApi, username: str = '') -> str:
    if not username:
        user = boosty_session.current_user
        if user is None:
            raise ValueError('Username is required')
        return user['name']
    return username


def get_media(
    boosty_session: BoostyApi,
    username: str = '',
    media_type: MediaType = MediaType.ALL,
    limit: t.Optional[int] = None,
    offset: t.Optional[str] = None,
    only_allowed: bool = False,
    start_date: t.Optional[date] = None,
    end_date: t.Optional[date] = None,
) -> Collection:
    """
    Returns uploaded media files of the user.

    Arguments:
        boosty_session (BoostyApi): Current session.
        username (str): Username, default current user or required.
        media_type (MediaType): Type of returned media, by default any.
        limit (int): The number of returned elements.
        offset (str): The offset from the beginning, returns the API Boosty.
        only_allowed (bool): Only available to viewing.
        start_date (date): Return from the specified date.
        end_date (date): Return by the specified date.
    """
    username = resolve_username(boosty_session, username)
    filter_data = Filter(
        limit=limit,
        offset=offset,
        only_allowed=only_allowed,
        start_date=start_date,
        end_date=end_date,
    )
    params = {
        'type': media_type,
        'limit_by': 'media',
        **filter_data.to_dict()
    }

    response_dict = boosty_session.request('get', f'/blog/{username}/media_album/', params=params)

    def iter_media_posts():
        for media_post in response_dict['data']['mediaPosts']:
            post = BasePost(**media_post['post'])

            for media in media_post['media']:
                yield Media(**media, post=post, username=username)

    return Collection(
        limit=limit,
        offset=response_dict['extra']['offset'],
        is_last=response_dict['extra']['isLast'],
        iterable=list(iter_media_posts()),
    )


def get_media_by_id(
    boosty_session: BoostyApi,
    post_id: str,
    media_id: str,
    username: str = '',
) -> t.Dict[str, t.Any]:
    """Returns the user media file with the passed identifier."""
    post = get_post(boosty_session, post_id, username)

    for media in post.iter_media():
        if media['id'] == media_id:
            return media

    raise BoostyError(f'Media file with ID {media_id} not found.')


def get_post(
    boosty_session: BoostyApi,
    post_id: str,
    username: str = '',
) -> Post:
    """Returns the user post with the passed identifier."""
    username = resolve_username(boosty_session, username)
    return Post(**boosty_session.request('get', f'/blog/{username}/post/{post_id}'))


def get_posts(
    boosty_session: BoostyApi,
    username: str = '',
    limit: t.Optional[int] = None,
    offset: t.Optional[str] = None,
    only_allowed: bool = False,
    start_date: t.Optional[date] = None,
    end_date: t.Optional[date] = None,
) -> Collection:
    """
    Returns blog posts of the user.

    Arguments:
        boosty_session (BoostyApi): Current session.
        username (str): Username, default current user or required.
        limit (int): The number of returned elements.
        offset (str): The offset from the beginning.
        only_allowed (bool): Only available to viewing.
        start_date (date): Return from the specified date.
        end_date (date): Return by the specified date.
    """
    username = resolve_username(boosty_session, username)
    filter_data = Filter(
        limit=limit,
        offset=offset,
        only_allowed=only_allowed,
        start_date=start_date,
        end_date=end_date,
    )
    params = filter_data.to_dict(remap_keys={'only_allowed': 'is_only_allowed'})

    response_dict = boosty_session.request('get', f'/blog/{username}/post/', params=params)

    return Collection(
        limit=limit,
        offset=response_dict['extra']['offset'],
        is_last=response_dict['extra']['isLast'],
        iterable=[Post(**i) for i in response_dict['data']],
        extra={
            'username': username,
        },
    )


def get_profile(boosty_session: BoostyApi, username: str) -> t.Dict[str, t.Any]:
    """Returns a user by username."""
    return boosty_session.request('get', f'/blog/{username}')


def get_profile_by_url(boosty_session: BoostyApi, url: str) -> t.Dict[str, t.Any]:
    """Returns a user using a URL containing their name."""
    match = re.search(r'//boosty.to/(.+?)/', url + '/')

    if not match:
        raise ValueError(f'The passed URL {url!r} is not a Boosty page.')

    return get_profile(boosty_session, username=match.group(1))


def get_subscriptions(
    boosty_session: BoostyApi,
    limit: t.Optional[int] = None,
    offset: t.Optional[int] = None,
) -> Collection:
    """
    Returns the subscriptions of the current user.

    Arguments:
        boosty_session (BoostyApi): Current session.
        limit (int): The number of returned elements.
        offset (str): The offset from the beginning.
    """
    filter_data = Filter(limit=limit, offset=offset)

    params: t.Dict[str, t.Any] = {
        'with_follow': 'true',
        **filter_data.to_dict()
    }

    response_dict = boosty_session.request('get', '/user/subscriptions', params=params)

    limit = response_dict.pop('limit')
    offset = response_dict.pop('offset')

    return Collection(
        limit=limit,
        offset=offset,
        is_last=limit + offset > response_dict['total'],
        iterable=response_dict.pop('data'),
        extra=response_dict,
    )


def search(
    boosty_session: BoostyApi,
    q: str,
    limit: int = 10,
    offset: t.Optional[str] = None,
    only_allowed: bool = False,
    only_bought: bool = False,
    start_date: t.Optional[date] = None,
    end_date: t.Optional[date] = None,
) -> t.Dict[str, t.Any]:
    """Search publications by authors you follow."""
    filter_data = Filter(
        limit=limit,
        offset=offset,
        only_allowed=only_allowed,
        start_date=start_date,
        end_date=end_date,
    )
    params: t.Dict[str, t.Any] = {
        'search_query': q,
        **filter_data.to_dict()
    }

    if only_bought:
        params['only_bought'] = 'true'

    return boosty_session.request('get', '/search/feed/post/', params=params)
