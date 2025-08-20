import typing as t
from _typeshed import Incomplete

__all__ = ['exists', 'glob', 'iglob', 'makedirs', 'rename', 'symlink']

exists: Incomplete
makedirs: Incomplete
rename: Incomplete

def glob(pathname: t.AnyStr, *, root_dir: t.AnyStr | None = None, **kwargs: t.Any) -> t.Sequence[str]: ...
def iglob(pathname: t.AnyStr, *, root_dir: t.AnyStr | None = None, **kwargs: t.Any) -> t.Iterator[t.AnyStr]: ...
def symlink(src: t.AnyStr, dst: t.AnyStr) -> None: ...
