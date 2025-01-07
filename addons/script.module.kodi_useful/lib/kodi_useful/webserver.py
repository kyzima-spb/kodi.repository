from __future__ import annotations

import sys
from functools import cached_property, partial
from http import server, HTTPStatus
import mimetypes
import json
import pathlib
import shutil
import socket
from string import Template
import threading
import typing as t
from urllib.parse import urlsplit

from .core import QueryParams

try:
    import xbmcaddon
    from xbmcvfs import translatePath
except ImportError:
    pass

if t.TYPE_CHECKING:
    from urllib.parse import SplitResult


PathLike = t.Union[str, pathlib.Path]


__all__ = (
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


class Response(t.NamedTuple):
    """Response object. Contains fields: response body, status, and headers."""

    status: int = HTTPStatus.OK
    body: t.Union[str, bytes] = b''
    headers: t.Optional[t.Dict[str, str]] = None

    def get_body(self) -> bytes:
        if isinstance(self.body, bytes):
            return self.body
        return self.body.encode('utf-8')

    def get_headers(self) -> t.Dict[str, str]:
        return {} if self.headers is None else self.headers


class HTTPError(Exception):
    def __init__(self, status: HTTPStatus) -> None:
        self.status = status


class HTTPRequestHandler(server.BaseHTTPRequestHandler):
    def __init__(
        self,
        *args: t.Any,
        url_handlers: t.Dict[str, t.Dict[str, t.Callable]],
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
    def url(self) -> SplitResult:
        """
        Returns the parsed URL of the request from 5 components:
        <scheme>://<netloc>/<path>?<query>#<fragment>
        """
        return urlsplit(self.path)

    def process_request(self) -> None:
        method = self.command.lower()
        # self.request

        if self.url.path.startswith('/static'):
            if method not in ('get', 'head'):
                return self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            return self.send_static()

        path = self.url.path.rstrip('/') or '/'

        if path not in self.url_handlers:
            return self.send_error(HTTPStatus.NOT_FOUND)

        handlers = self.url_handlers[path]

        if method not in handlers:
            return self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)

        handler = handlers[method]

        try:
            resp = handler(self)

            if isinstance(resp, HTTPStatus):
                resp = (resp,)

            if not isinstance(resp, tuple):
                return self.send_error(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    'Response must be HTTPStatus or tuple'
                )

            r = Response(*resp)

            self.send_response(r.status)

            for name, value in r.get_headers().items():
                self.send_header(name, value)

            self.end_headers()

            self.wfile.write(r.get_body())
        except HTTPError as err:
            self.send_error(err.status)
        except Exception as err:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(err))

    do_DELETE = process_request
    do_GET = process_request
    do_HEAD = process_request
    do_POST = process_request
    do_PUT = process_request

    def send_json(self, data, status=HTTPStatus.OK):
        try:
            json_string = json.dumps(data)
        except TypeError:
            return self.send_error(HTTPStatus.BAD_REQUEST)

        return status, json_string, {
            'Content-Type': 'application/json',
            'Content-Length': str(len(json_string)),
        }

    def send_static(self) -> None:
        path = self.root_dir / self.url.path.lstrip('/')

        try:
            f = path.open('rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return None

        fs = path.stat()

        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', guess_type(path))
        self.send_header('Content-Length', str(fs.st_size))
        self.end_headers()

        try:
            if self.command != 'HEAD':
                shutil.copyfileobj(f, self.wfile)
        finally:
            f.close()

        return None

    def render_template(self, name, **kwargs):
        path = self.root_dir / name
        tmpl = Template(path.read_text())
        content = tmpl.substitute(**kwargs)
        return HTTPStatus.OK, content, {
            'Content-type': guess_type(path),
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
            addon_path = translatePath(xbmcaddon.Addon().getAddonInfo('path'))
            root_dir = pathlib.Path(addon_path) / 'resources' / 'www'
        else:
            root_dir = pathlib.Path(root_dir)

        self._url_handlers = {}
        self._handler = partial(
            HTTPRequestHandler, url_handlers=self._url_handlers, root_dir=root_dir
        )

    def delete(self, path: str):
        """Registers a DELETE request handler for the specified path."""
        return self.register_handler(path, method='delete')

    def get(self, path: str):
        """Registers a GET request handler for the specified path."""
        return self.register_handler(path, method='get')

    def log(self, msg: str) -> None:
        print(msg, file=sys.stderr)

    def is_running(self) -> bool:
        """Returns true if the web server is running, false otherwise."""
        return self._httpd is not None

    def post(self, path: str):
        """Registers a POST request handler for the specified path."""
        return self.register_handler(path, method='post')

    def put(self, path: str):
        """Registers a PUT request handler for the specified path."""
        return self.register_handler(path, method='put')

    def register_handler(self, path: str, method: str):
        def decorator(handler):
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
            self.log(err)
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
        if not self.is_running():
            return None

        self._httpd.shutdown()
        self._httpd.socket.close()
        self._httpd = None

        if self._httpd_thread is not None:
            self._httpd_thread.join()
            self._httpd_thread = None

        self.log('Server stopped')

        return None


if __name__ == '__main__':
    srv = HTTPServer(port=9000, root_dir='.')

    @srv.post('/')
    def f(request_handler: HTTPRequestHandler):
        print(request_handler.form.get('test'))
        return request_handler.send_json({'status': True})

    srv.start()
