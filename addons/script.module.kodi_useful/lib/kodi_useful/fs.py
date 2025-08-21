import glob as _glob
import os
import typing as t

import xbmcvfs


__all__ = (
    'exists',
    'get_suffix',
    'glob',
    'iglob',
    'makedirs',
    'remove',
    'rename',
    'symlink',
)


exists = xbmcvfs.exists
makedirs = xbmcvfs.mkdirs
remove = xbmcvfs.delete
rename = xbmcvfs.rename


def _encode(path, encoding='utf-8'):
    if isinstance(path, str):
        return path.encode(encoding)
    return path


def get_suffix(pathname: t.AnyStr) -> str:
    """Returns the extension from a filename."""
    _, ext = os.path.splitext(_encode(pathname))
    return ext.decode()


def glob(
    pathname: t.AnyStr,
    *,
    root_dir: t.Optional[t.AnyStr] = None,
    **kwargs: t.Any,
) -> t.Sequence[str]:
    return [i.decode() for i in iglob(pathname, root_dir=root_dir, **kwargs)]


def iglob(
    pathname: t.AnyStr,
    *,
    root_dir: t.Optional[t.AnyStr] = None,
    **kwargs: t.Any,
) -> t.Iterator[t.AnyStr]:
    if root_dir is not None:
        root_dir = _encode(root_dir)
    return _glob.iglob(_encode(pathname), root_dir=root_dir, **kwargs)


def symlink(
    src: t.AnyStr,
    dst: t.AnyStr,
) -> None:
    os.symlink(_encode(src), _encode(dst))
