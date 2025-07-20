from _typeshed import Incomplete
from http import HTTPStatus as HTTPStatus

class KodiUsefulError(Exception): ...

class HTTPError(KodiUsefulError):
    status: Incomplete
    message: Incomplete
    def __init__(self, status: HTTPStatus, message: str = '') -> None: ...

class RouterError(KodiUsefulError): ...
class ObjectNotFound(KodiUsefulError):
    """No record with the specified ID was found in the database."""
class ValidationError(KodiUsefulError):
    """Any error in validating incoming data."""
