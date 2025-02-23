import pathlib
import typing as t
from .core import QueryParams
from _typeshed import Incomplete
from functools import cached_property
from http import HTTPStatus, server
from urllib.parse import SplitResult

__all__ = ['HTTPRequestHandler', 'HTTPError', 'HTTPServer', 'Response']

PathLike = str | pathlib.Path

class Response(t.NamedTuple):
    """Response object. Contains fields: response body, status, and headers."""
    status: int = ...
    body: str | bytes = ...
    headers: dict[str, str] | None = ...
    def get_body(self) -> bytes: ...
    def get_headers(self) -> dict[str, str]: ...

class HTTPError(Exception):
    status: Incomplete
    def __init__(self, status: HTTPStatus) -> None: ...

class HTTPRequestHandler(server.BaseHTTPRequestHandler):
    url_handlers: Incomplete
    root_dir: Incomplete
    def __init__(self, *args: t.Any, url_handlers: dict[str, dict[str, t.Callable]], root_dir: PathLike, **kwargs: t.Any) -> None: ...
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
    def process_request(self) -> None: ...
    do_DELETE = process_request
    do_GET = process_request
    do_HEAD = process_request
    do_POST = process_request
    do_PUT = process_request
    def send_json(self, data, status=...): ...
    def send_static(self) -> None: ...
    def render_template(self, name, **kwargs): ...

class HTTPServer:
    _address: Incomplete
    _httpd: Incomplete
    _httpd_thread: Incomplete
    _url_handlers: Incomplete
    _handler: Incomplete
    def __init__(self, host: str = 'localhost', port: int = 0, root_dir: PathLike = '') -> None: ...
    def delete(self, path: str):
        """Registers a DELETE request handler for the specified path."""
    def get(self, path: str):
        """Registers a GET request handler for the specified path."""
    def log(self, msg: str) -> None: ...
    def is_running(self) -> bool:
        """Returns true if the web server is running, false otherwise."""
    def post(self, path: str):
        """Registers a POST request handler for the specified path."""
    def put(self, path: str):
        """Registers a PUT request handler for the specified path."""
    def register_handler(self, path: str, method: str): ...
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
