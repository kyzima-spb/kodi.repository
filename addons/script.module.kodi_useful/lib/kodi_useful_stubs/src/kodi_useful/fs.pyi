import typing as t
from _typeshed import Incomplete

__all__ = ['exists', 'get_suffix', 'glob', 'iglob', 'makedirs', 'remove', 'rename', 'symlink']

exists: Incomplete
makedirs: Incomplete
remove: Incomplete
rename: Incomplete

def get_suffix(pathname: t.AnyStr) -> str: ...
def glob(pathname: t.AnyStr, *, root_dir: t.AnyStr | None = None, **kwargs: t.Any) -> t.Sequence[str]: ...
def iglob(pathname: t.AnyStr, *, root_dir: t.AnyStr | None = None, **kwargs: t.Any) -> t.Iterator[t.AnyStr]: ...
def symlink(src: t.AnyStr, dst: t.AnyStr) -> None: ...
