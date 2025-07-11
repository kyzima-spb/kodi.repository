import sqlite3
import typing as t
from _typeshed import Incomplete
from dataclasses import dataclass
from types import TracebackType
from typing import Any

__all__ = ['select', 'Connection', 'Model']

PrimaryKey = Any | tuple[Any, ...] | dict[str, Any]

def select(model_class: type['Model']) -> SelectStatement: ...

@dataclass(frozen=True)
class QueryResult:
    cursor: sqlite3.Cursor
    row_factory: t.Callable | None = ...
    def __iter__(self) -> t.Iterator[t.Any]: ...
    def fetchall(self) -> t.Sequence[t.Any]: ...
    def fetchone(self) -> t.Any | None: ...
    def scalar(self) -> t.Any | None: ...
    def scalars(self) -> t.Sequence[t.Any]: ...
    def __init__(self, cursor, row_factory=...) -> None: ...

class Connection:
    _filename: Incomplete
    _conn: Incomplete
    def __init__(self, filename: str) -> None: ...
    def __enter__(self) -> Connection: ...
    def __exit__(self, err_type: type[BaseException] | None, err: BaseException | None, tb: TracebackType) -> None: ...
    def _get_connection(self) -> sqlite3.Connection: ...
    def close(self) -> None: ...
    def commit(self) -> None: ...
    def execute(self, stmt: str | SelectStatement, parameters: t.Sequence[t.Any] | dict[str, t.Any] = (), **payload: t.Any) -> QueryResult: ...
    def executescript(self, sql_script: str, raw: bool = False) -> None: ...
    def query(self, stmt: str | SelectStatement, parameters: t.Sequence[t.Any] | dict[str, t.Any] = (), row_factory: t.Callable | type['Model'] | None = ..., **payload: t.Any) -> QueryResult: ...
    def rollback(self) -> None: ...

@dataclass(frozen=True)
class SelectStatement:
    query: str
    model_class: type['Model'] | None = ...
    def __str__(self) -> str: ...
    def __add__(self, other: str) -> SelectStatement: ...
    def limit(self, value: int) -> SelectStatement: ...
    def offset(self, value: int) -> SelectStatement: ...
    def order_by(self, name: str, desc: bool = False) -> SelectStatement: ...
    def __init__(self, query, model_class=...) -> None: ...

class SQLQueryBuilder:
    _model_class: Incomplete
    def __init__(self, model_class: type['Model']) -> None: ...
    def _where_pk(self) -> str: ...
    def delete(self) -> str: ...
    def insert(self) -> str: ...
    def select(self) -> SelectStatement: ...
    def select_by_pk(self) -> SelectStatement: ...
    def update(self) -> str: ...

@dataclass
class Model:
    _table_name_: t.ClassVar[str | None] = ...
    _primary_key_: t.ClassVar[tuple[str, ...]] = ...
    def as_dict(self) -> dict[str, t.Any]: ...
    def delete(self) -> None: ...
    @classmethod
    def find(cls, id_: PrimaryKey) -> Model | None: ...
    @classmethod
    def get_builder(cls) -> SQLQueryBuilder: ...
    @classmethod
    def get_connection(cls) -> Connection: ...
    def get_id(self) -> PrimaryKey | None: ...
    @classmethod
    def get_primary_key(cls) -> tuple[str, ...]: ...
    @classmethod
    def get_table_columns(cls) -> tuple[str, ...]: ...
    @classmethod
    def get_table_name(cls) -> str: ...
    @classmethod
    def is_autoincrement_pk(cls) -> bool: ...
    def save(self) -> None: ...
    def set_id(self, id_: PrimaryKey) -> None: ...
