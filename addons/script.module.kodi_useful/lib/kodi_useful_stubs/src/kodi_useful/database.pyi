import sqlite3
import typing as t
from _typeshed import Incomplete
from dataclasses import dataclass
from types import TracebackType
from typing import Any

__all__ = ['select', 'Connection', 'Model', 'SQLStatement']

PrimaryKey = Any | tuple[Any, ...] | dict[str, Any]

def select(model_class: type[Model]) -> SelectStatement: ...

class Connection:
    _filename: Incomplete
    _conn: Incomplete
    def __init__(self, filename: str) -> None: ...
    def __enter__(self) -> Connection: ...
    def __exit__(self, err_type: type[BaseException] | None, err: BaseException | None, tb: TracebackType) -> None: ...
    def _get_connection(self) -> sqlite3.Connection: ...
    def close(self) -> None: ...
    def commit(self) -> None: ...
    def execute(self, stmt: SQLStatement, **payload: t.Any) -> sqlite3.Cursor: ...
    def executescript(self, sql_script: str) -> sqlite3.Cursor: ...
    def query(self, stmt: SelectStatement, model_class: type[Model] | None = None, **payload: t.Any) -> sqlite3.Cursor: ...
    def rollback(self) -> None: ...

class SQLStatement:
    query: Incomplete
    def __init__(self, query: str) -> None: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __add__(self, other: str) -> SQLStatement: ...
    @property
    def placeholders(self) -> t.Sequence[str]: ...

class SelectStatement(SQLStatement):
    model_class: Incomplete
    def __init__(self, query: str, model_class: type[Model] | None = None) -> None: ...
    def __add__(self, other: str) -> SelectStatement: ...
    def limit(self, value: int) -> SelectStatement: ...
    def offset(self, value: int) -> SelectStatement: ...
    def order_by(self, name: str, desc: bool = False) -> SelectStatement: ...

class SQLQueryBuilder:
    _model_class: Incomplete
    def __init__(self, model_class: type[Model]) -> None: ...
    def _where_pk(self) -> str: ...
    def delete(self) -> SQLStatement: ...
    def insert(self) -> SQLStatement: ...
    def select(self) -> SelectStatement: ...
    def select_by_pk(self) -> SelectStatement: ...
    def update(self) -> SQLStatement: ...

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
