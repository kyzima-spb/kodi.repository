import json
import pathlib
import typing as t
from ..exceptions import HTTPError as HTTPError
from ..routing import QueryParams
from _typeshed import Incomplete
from dataclasses import dataclass
from functools import cached_property
from http import HTTPStatus, server
from urllib.parse import SplitResult

__all__ = ['validate', 'HTTPRequestHandler', 'HTTPError', 'HTTPServer', 'Response']

_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])
T = t.TypeVar('T')
Headers = dict[str, str]
PathLike = str | pathlib.Path

def validate(schema: type[T], payload: dict[str, t.Any]) -> T: ...

class JSONEncoder(json.JSONEncoder):
    def default(self, obj: t.Any) -> t.Any: ...

@dataclass
class Response:
    """Response object. Contains fields: response body, status, and headers."""
    status: int = ...
    body: str | bytes = ...
    headers: Headers | None = ...
    def get_body(self) -> bytes: ...
    def get_headers(self) -> Headers: ...
    def __init__(self, status=..., body=..., headers=...) -> None: ...

@dataclass
class JSONResponse(Response):
    body: t.Any = ...
    def __post_init__(self) -> None: ...
    def get_headers(self) -> Headers: ...
    def __init__(self, status=..., body=..., headers=...) -> None: ...

class HTTPRequestHandler(server.BaseHTTPRequestHandler):
    url_handlers: Incomplete
    root_dir: Incomplete
    def __init__(self, *args: t.Any, url_handlers: dict[str, URLHandler], root_dir: PathLike, **kwargs: t.Any) -> None: ...
    @cached_property
    def form(self) -> QueryParams: ...
    @cached_property
    def json(self) -> t.Any:
        """Returns the request body parsed from JSON format, otherwise an error."""
    @cached_property
    def post_data(self) -> bytes: ...
    @cached_property
    def query(self) -> QueryParams:
        """Returns the URL query string parameters."""
    @cached_property
    def url(self) -> SplitResult:
        """
        Returns the parsed URL of the request from 5 components:
        <scheme>://<netloc>/<path>?<query>#<fragment>
        """
    def end_headers(self) -> None: ...
    def process_request(self) -> None: ...
    do_DELETE = process_request
    do_GET = process_request
    do_HEAD = process_request
    do_POST = process_request
    do_PUT = process_request
    do_OPTIONS = process_request
    def send_error(self, status: HTTPStatus | int, message: str | None = None, explain: str | None = None, detail: t.Any | None = None) -> None: ...
    def send_headers(self, headers: Headers) -> None: ...
    def send_json(self, data: t.Any, status: HTTPStatus = ...) -> JSONResponse: ...
    def send_static(self) -> None: ...
    def render_template(self, name: str, **kwargs: t.Any) -> ResponseValue: ...

class HTTPServer:
    _address: Incomplete
    _httpd: Incomplete
    _httpd_thread: Incomplete
    _url_handlers: Incomplete
    _handler: Incomplete
    def __init__(self, host: str = 'localhost', port: int = 0, root_dir: PathLike = '') -> None: ...
    def delete(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a DELETE request handler for the specified path."""
    def get(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a GET request handler for the specified path."""
    def log(self, msg: str) -> None: ...
    def is_running(self) -> bool:
        """Returns true if the web server is running, false otherwise."""
    def post(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a POST request handler for the specified path."""
    def put(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a PUT request handler for the specified path."""
    def register_handler(self, path: str, method: str) -> t.Callable[[_F], _F]: ...
    def restart(self) -> None:
        """Restarts the web server."""
    def start(self, run_in_thread: bool = False) -> None:
        """
        Starts the web server.

        Arguments:
            run_in_thread (bool): specifies whether to start the server in a separate thread.
        """
    def set_address(self, host: str, port: int) -> None:
        """Changes server address without restarting."""
    def stop(self) -> None:
        """Stop a running server."""
