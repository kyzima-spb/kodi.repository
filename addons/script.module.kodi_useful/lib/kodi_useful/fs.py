import glob as _glob
import os
import typing as t


__all__ = (
    'glob',
    'iglob',
    'makedirs',
    'rename',
    'symlink',
)


def _encode(path, encoding='utf-8'):
    if isinstance(path, str):
        return path.encode(encoding)
    return path


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


def makedirs(pathname: t.AnyStr) -> None:
    os.makedirs(_encode(pathname), mode=0o755, exist_ok=True)


def rename(
    src: t.AnyStr,
    dst: t.AnyStr,
) -> None:
    os.rename(_encode(src), _encode(dst))


def symlink(
    src: t.AnyStr,
    dst: t.AnyStr,
) -> None:
    os.symlink(_encode(src), _encode(dst))
