from _typeshed import Incomplete
from http import HTTPStatus as HTTPStatus

class KodiUsefulError(Exception): ...

class HTTPError(KodiUsefulError):
    status: Incomplete
    message: Incomplete
    def __init__(self, status: HTTPStatus, message: str = '') -> None: ...

class RouterError(KodiUsefulError): ...
class ObjectNotFound(KodiUsefulError):
    """No object with the specified lookup was found."""
class MultipleObjectsFound(KodiUsefulError):
    """Multiple objects were found but need one."""

class ValidationError(KodiUsefulError):
    """Any error in validating incoming data."""
    message: Incomplete
    errors: Incomplete
    def __init__(self, message: str = '', errors: dict[str, str] | None = None) -> None: ...
