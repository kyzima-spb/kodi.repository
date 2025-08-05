import typing as t

import requests

if t.TYPE_CHECKING:
    from .boosty_api import BoostyApi


__all__ = ('BoostyError', 'AuthError', 'BoostyApiError', 'LoginRequired')


class BoostyError(Exception):
    def __init__(self, error: t.Union[t.Dict[str, str], str]) -> None:
        if isinstance(error, dict):
            self.error_code = error.get('error')
            self.error_description = error.get('error_description', str(error))
        else:
            self.error_code = None
            self.error_description = error

    def __str__(self) -> str:
        return self.error_description


class AuthError(BoostyError):
    pass


class LoginRequired(AuthError):
    pass


class BoostyApiError(BoostyError):
    def __init__(
        self,
        message: str,
        boosty: 'BoostyApi',
        response: requests.Response,
        request_kwargs: t.Dict[str, t.Any],
    ) -> None:
        self.message = message
        self.boosty = boosty
        self.response = response
        self.request_kwargs = request_kwargs

    def retry_request(self) -> t.Any:
        return self.boosty.request(**self.request_kwargs)

    def __str__(self) -> str:
        return '%s for %s' % (self.message, self.response.url)
