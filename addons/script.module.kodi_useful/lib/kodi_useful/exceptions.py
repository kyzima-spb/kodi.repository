from http import HTTPStatus
import typing as t


class KodiUsefulError(Exception):
    pass


class HTTPError(KodiUsefulError):
    def __init__(self, status: HTTPStatus, message: str = '') -> None:
        self.status = status
        self.message = message


class RouterError(KodiUsefulError):
    pass


class ObjectNotFound(KodiUsefulError):
    """No record with the specified ID was found in the database."""


class ValidationError(KodiUsefulError):
    """Any error in validating incoming data."""

    def __init__(self, message: str = '', errors: t.Optional[t.Dict[str, str]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or {}
