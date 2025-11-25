from dataclasses import dataclass, fields, field, is_dataclass, MISSING
from datetime import datetime
from functools import cached_property, partial
from http import server, HTTPStatus
import mimetypes
import json
import pathlib
import shutil
import socket
from string import Template
import threading
import traceback
import typing as t
from urllib.parse import urlsplit

from requests import HTTPError as RequestsHTTPError

from ..core import current_addon
from ..routing import QueryParams
from ..exceptions import HTTPError, ObjectNotFound, ValidationError

if t.TYPE_CHECKING:
    from urllib.parse import SplitResult


_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])
T = t.TypeVar('T')
Headers = t.Dict[str, str]
PathLike = t.Union[str, pathlib.Path]
ResponseValue = t.Union[
    'Response',
    HTTPStatus,
    t.Tuple[HTTPStatus, t.Union[str, bytes]],
    t.Tuple[HTTPStatus, t.Union[str, bytes], Headers],
]
URLHandler = t.Dict[str, t.Callable[['HTTPRequestHandler'], ResponseValue]]


__all__ = (
    'validate',
    'HTTPRequestHandler',
    'HTTPError',
    'HTTPServer',
    'Response',
)


def guess_type(path: PathLike) -> str:
    """Guesses and returns the mimetype for the given path or URL."""
    ctype, _ = mimetypes.guess_type(path)
    if ctype is None:
        ctype = 'application/octet-stream'
    return ctype


def validate(schema: t.Type[T], payload: t.Dict[str, t.Any]) -> T:
    if not is_dataclass(schema):
        raise TypeError('The schema argument must be a dataclass.')

    declared_fields = {f.name: f for f in fields(schema)}
    errors = {}

    for name, value in payload.items():
        fld = declared_fields.pop(name, None)

        if fld is None:
            errors[name] = f'Missing field {name!r} in schema.'
        else:
            allowed_types = t.get_args(fld.type) or (fld.type,)

            if not isinstance(value, allowed_types):
                allowed_types_string = ', '.join(i.__name__ for i in allowed_types if i is not type(None))
                errors[name] = f'Field {name!r} has an incompatible data type, requires: {allowed_types_string}.'

    for name, fld in declared_fields.items():
        if fld.default is MISSING and fld.default_factory is MISSING:
            errors[name] = f'Field {name!r} is required.'

    if errors:
        raise ValidationError(errors=errors)

    return t.cast(T, schema(**payload))


class JSONEncoder(json.JSONEncoder):
    def default(self, obj: t.Any) -> t.Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class Response:
    """Response object. Contains fields: response body, status, and headers."""

    status: int = HTTPStatus.OK
    body: t.Union[str, bytes] = b''
    headers: t.Optional[Headers] = None

    def get_body(self) -> bytes:
        if isinstance(self.body, bytes):
            return self.body
        return self.body.encode('utf-8')

    def get_headers(self) -> Headers:
        headers = self.headers or {}
        headers['Content-Length'] = str(len(self.get_body()))
        return headers


@dataclass
class JSONResponse(Response):
    body: t.Any = ''

    def __post_init__(self) -> None:
        if not isinstance(self.body, (str, bytes)):
            try:
                self.body = json.dumps(self.body, cls=JSONEncoder)
            except TypeError as err:
                raise HTTPError(
                    HTTPStatus.BAD_REQUEST,
                    'Passed value is not JSON serializable.',
                ) from err

    def get_headers(self) -> Headers:
        headers = super().get_headers()
        headers['Content-Type'] = 'application/json'
        return headers


class HTTPRequestHandler(server.BaseHTTPRequestHandler):
    def __init__(
        self,
        *args: t.Any,
        url_handlers: t.Dict[str, URLHandler],
        root_dir: PathLike,
        **kwargs: t.Any,
    ) -> None:
        self.url_handlers = url_handlers
        self.root_dir = pathlib.Path(root_dir)
        super().__init__(*args, **kwargs)

    @cached_property
    def form(self) -> QueryParams:
        ctype = self.headers.get('Content-Type', '')

        if ctype.startswith('multipart/form-data'):
            raise HTTPError(HTTPStatus.NOT_IMPLEMENTED)

        return QueryParams(self.post_data.decode('utf-8'))

    @cached_property
    def json(self) -> t.Any:
        """Returns the request body parsed from JSON format, otherwise an error."""
        try:
            return json.loads(self.post_data.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPError(HTTPStatus.BAD_REQUEST)

    @cached_property
    def post_data(self) -> bytes:
        content_length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(content_length)

    @cached_property
    def query(self) -> QueryParams:
        """Returns the URL query string parameters."""
        return QueryParams(self.url.query)

    @cached_property
    def url(self) -> 'SplitResult':
        """
        Returns the parsed URL of the request from 5 components:
        <scheme>://<netloc>/<path>?<query>#<fragment>
        """
        return urlsplit(self.path)

    def end_headers(self) -> None:
        self.send_headers({
            'Access-Control-Allow-Origin': self.headers.get('Origin', '*'),
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true',
        })
        super().end_headers()

    def process_request(self) -> None:
        method = self.command.lower()

        if self.url.path.startswith('/static'):
            if method not in ('get', 'head'):
                return self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            return self.send_static()

        path = self.url.path.rstrip('/') or '/'

        if path not in self.url_handlers:
            return self.send_error(HTTPStatus.NOT_FOUND)

        handlers = self.url_handlers[path]

        if method == 'options':
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            return None
        elif method not in handlers:
            return self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)

        handler = handlers[method]

        try:
            resp = handler(self)

            if isinstance(resp, Response):
                r = resp
            elif isinstance(resp, HTTPStatus):
                r = Response(status=resp)
            elif isinstance(resp, tuple):
                if len(resp) == 1:
                    r = Response(status=resp[0])
                elif len(resp) == 2:
                    r = Response(status=resp[0], body=resp[1])
                elif len(resp) == 3:
                    r = Response(status=resp[0], body=resp[1], headers=resp[2])
                else:
                    return self.send_error(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        'The response must be a tuple of one to three elements.'
                    )
            else:
                return self.send_error(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    'Response must be Response, HTTPStatus or tuple.'
                )

            self.send_response(r.status)
            self.send_headers(r.get_headers())
            self.end_headers()

            self.wfile.write(r.get_body())
        except ObjectNotFound as err:
            self.send_error(HTTPStatus.NOT_FOUND, str(err))
        except ValidationError as err:
            self.send_error(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                err.message,
                detail={'errors': err.errors},
            )
        except HTTPError as err:
            self.send_error(err.status, err.message)
        except RequestsHTTPError as err:
            detail = None

            if err.response.headers.get('Content-Type', '') == 'application/json':
                detail = err.response.json()

            self.send_error(
                err.response.status_code,
                f'{err.response.reason} for url {err.request.url!r}',
                detail=detail,
            )
        except Exception as err:
            tb_str = traceback.format_exc()
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(err), detail=tb_str)

    do_DELETE = process_request
    do_GET = process_request
    do_HEAD = process_request
    do_POST = process_request
    do_PUT = process_request
    do_OPTIONS = process_request

    def send_error(
        self,
        status: t.Union[HTTPStatus, int],
        message: t.Optional[str] = None,
        explain: t.Optional[str] = None,
        detail: t.Optional[t.Any] = None,
    ) -> None:
        if 'application/json' in self.headers.get('Accept', ''):
            r = JSONResponse(status=status, body={
                'status': status.value if isinstance(status, HTTPStatus) else status,
                'message': message,
                'detail': detail or {},
            })

            self.send_response(r.status)
            self.send_headers(r.get_headers())
            self.end_headers()

            self.wfile.write(r.get_body())
        else:
            super().send_error(status, message, explain)

    def send_headers(self, headers: Headers) -> None:
        for name, value in headers.items():
            self.send_header(name, value)

    def send_json(self, data: t.Any, status: HTTPStatus = HTTPStatus.OK) -> JSONResponse:
        return JSONResponse(body=data, status=status)

    def send_static(self) -> None:
        path = self.root_dir / self.url.path.lstrip('/')

        try:
            f = path.open('rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return None

        fs = path.stat()

        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', guess_type(path))
        self.send_header('Content-Length', str(fs.st_size))
        self.end_headers()

        try:
            if self.command != 'HEAD':
                shutil.copyfileobj(f, self.wfile)
        finally:
            f.close()

        return None

    def render_template(self, name: str, **kwargs: t.Any) -> ResponseValue:
        path = self.root_dir / name
        tmpl = Template(path.read_text())
        content = tmpl.substitute(**kwargs)
        return HTTPStatus.OK, content, {
            'Content-Type': guess_type(path),
            'Content-Length': str(len(content)),
        }


class HTTPServer:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 0,
        root_dir: PathLike = '',
    ) -> None:
        self._address = (host, port)
        self._httpd: t.Optional[server.HTTPServer] = None
        self._httpd_thread: t.Optional[threading.Thread] = None

        if not root_dir:
            root_dir = current_addon.get_path('resources', 'www')

        self._url_handlers: t.Dict[str, URLHandler] = {}
        self._handler = partial(
            HTTPRequestHandler, url_handlers=self._url_handlers, root_dir=root_dir
        )

    def delete(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a DELETE request handler for the specified path."""
        return self.register_handler(path, method='delete')

    def get(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a GET request handler for the specified path."""
        return self.register_handler(path, method='get')

    def log(self, msg: str) -> None:
        current_addon.logger.info(msg)

    def is_running(self) -> bool:
        """Returns true if the web server is running, false otherwise."""
        return self._httpd is not None

    def post(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a POST request handler for the specified path."""
        return self.register_handler(path, method='post')

    def put(self, path: str) -> t.Callable[[_F], _F]:
        """Registers a PUT request handler for the specified path."""
        return self.register_handler(path, method='put')

    def register_handler(self, path: str, method: str) -> t.Callable[[_F], _F]:
        def decorator(handler: _F) -> _F:
            handlers = self._url_handlers.setdefault(path, {})
            handlers[method] = handler
            return handler
        return decorator

    def restart(self) -> None:
        """Restarts the web server."""
        if self.is_running():
            run_in_thread = self._httpd_thread is not None
            self.stop()
            self.start(run_in_thread=run_in_thread)

    def start(self, run_in_thread: bool = False) -> None:
        """
        Starts the web server.

        Arguments:
            run_in_thread (bool): specifies whether to start the server in a separate thread.
        """
        if self.is_running():
            return None

        try:
            self._httpd = server.ThreadingHTTPServer(self._address, self._handler)
        except socket.error as err:
            self.log(str(err))
            return None

        self.log('The server is running at http://%s:%d' % self._address)

        if run_in_thread:
            self._httpd_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._httpd_thread.start()
        else:
            self._httpd.serve_forever()

        return None

    def set_address(self, host: str, port: int) -> None:
        """Changes server address without restarting."""
        self._address = (host, port)

    def stop(self) -> None:
        """Stop a running server."""
        if self._httpd is None:
            return None

        self._httpd.shutdown()
        self._httpd.socket.close()
        self._httpd = None

        if self._httpd_thread is not None:
            self._httpd_thread.join()
            self._httpd_thread = None

        self.log('Server stopped')

        return None
