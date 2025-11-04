import atexit
from contextlib import contextmanager
from dataclasses import dataclass, fields
import datetime
from functools import cached_property, lru_cache, partial
import json
import os
import re
import sqlite3
import typing as t
from typing import Any, Dict, Tuple, Union
import uuid

from . import current_addon, fs
from .exceptions import ObjectNotFound


__all__ = ('select', 'Connection', 'Model')


PrimaryKey = Union[Any, Tuple[Any, ...], Dict[str, Any]]

sqlite3.register_adapter(datetime.date, lambda v: v.isoformat())
sqlite3.register_adapter(datetime.datetime, lambda v: v.isoformat())
sqlite3.register_adapter(dict, lambda v: json.dumps(v))
sqlite3.register_adapter(list, lambda v: json.dumps(v))

sqlite3.register_converter('date', lambda v: datetime.date.fromisoformat(v.decode()))
sqlite3.register_converter('datetime', lambda v: datetime.datetime.fromisoformat(v.decode()))
sqlite3.register_converter('timestamp', lambda v: datetime.datetime.fromtimestamp(int(v)))
sqlite3.register_converter('JSON', lambda v: json.loads(v.decode('utf-8')))


def model_row_factory(
    cursor: sqlite3.Cursor,
    row: t.Tuple[t.Any, ...],
    model_class: t.Type['Model'],
) -> 'Model':
    columns = [column[0] for column in cursor.description]
    return model_class(**{
        key: value
        for key, value in zip(columns, row)
    })


def select(model_class: t.Type['Model']) -> 'SelectStatement':
    table_name = model_class.get_table_name()
    columns = model_class.get_table_columns()
    columns_clause = ', '.join(columns)
    return SelectStatement(
        f'SELECT {columns_clause} FROM {table_name}',
        model_class=model_class,
    )


@dataclass(frozen=True)
class QueryResult:
    cursor: sqlite3.Cursor
    row_factory: t.Optional[t.Callable] = None

    def __iter__(self) -> t.Iterator[t.Any]:
        for row in self.cursor:
            yield self.row_factory(self.cursor, row) if callable(self.row_factory) else row

    def fetchall(self) -> t.Sequence[t.Any]:
        return list(self)

    def fetchone(self) -> t.Optional[t.Any]:
        return next(iter(self), None)

    def scalar(self) -> t.Optional[t.Any]:
        row = self.fetchone()
        return row[0] if row else None

    def scalars(self) -> t.Sequence[t.Any]:
        return [row[0] for row in self]


@dataclass
class Connection:
    path: str
    echo: bool = False

    @cached_property
    def connection(self) -> sqlite3.Connection:
        fs.makedirs(os.path.dirname(self.path))

        conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)

        if self.echo:
            conn.set_trace_callback(current_addon.logger.debug)

        conn.execute('PRAGMA foreign_keys = ON')
        atexit.register(conn.close)

        return conn

    def execute(
        self,
        stmt: t.Union[str, 'SelectStatement'],
        parameters: t.Union[t.Sequence[t.Any], t.Dict[str, t.Any]] = (),
        **payload: t.Any,
    ) -> QueryResult:
        if parameters and payload:
            raise ValueError('You can use either parameters or named arguments, but not both.')

        if payload:
            parameters = payload

        return QueryResult(
            cursor=self.connection.execute(str(stmt), parameters),
        )

    def executescript(self, sql_script: str, raw: bool = False) -> None:
        if raw:
            self.connection.executescript(sql_script)
        else:
            for stmt in sql_script.split(';'):
                self.connection.execute(stmt)

    def query(
        self,
        stmt: t.Union[str, 'SelectStatement'],
        parameters: t.Union[t.Sequence[t.Any], t.Dict[str, t.Any]] = (),
        row_factory: t.Optional[t.Union[t.Callable, t.Type['Model']]] = sqlite3.Row,
        **payload: t.Any,
    ) -> QueryResult:
        if parameters and payload:
            raise ValueError('You can use either parameters or named arguments, but not both.')

        if isinstance(stmt, SelectStatement) and stmt.model_class:
            row_factory = partial(model_row_factory, model_class=stmt.model_class)

        return QueryResult(
            cursor=self.connection.execute(str(stmt), parameters),
            row_factory=row_factory
        )

    @contextmanager
    def transaction(self):
        savepoint_name = f'sp_{uuid.uuid4().hex}'
        try:
            self.execute(f'SAVEPOINT {savepoint_name}')
            yield
            self.execute(f'RELEASE SAVEPOINT {savepoint_name}')
        except Exception:
            self.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
            self.execute(f'RELEASE SAVEPOINT {savepoint_name}')
            raise


@dataclass(frozen=True)
class SelectStatement:
    query: str
    model_class: t.Optional[t.Type['Model']] = None

    def __str__(self) -> str:
        return self.query

    def __add__(self, other: str) -> 'SelectStatement':
        if not isinstance(other, str):
            return NotImplemented
        return type(self)(query=self.query + other, model_class=self.model_class)

    def limit(self, value: int) -> 'SelectStatement':
        return self + ' LIMIT %d' % value

    def offset(self, value: int) -> 'SelectStatement':
        return self + ' OFFSET %d' % value

    def order_by(self, name: str, desc: bool = False) -> 'SelectStatement':
        direction = 'DESC' if desc else 'ASC'
        return self + (' ORDER BY %s %s' % (name, direction))


class SQLQueryBuilder:
    def __init__(self, model_class: t.Type['Model']) -> None:
        self._model_class = model_class

    def _where_pk(self) -> str:
        return ' AND '.join('{0} = :{0}'.format(name) for name in self._model_class.get_primary_key())

    def delete(self) -> str:
        return f'DELETE FROM {self._model_class.get_table_name()} WHERE {self._where_pk()}'

    def insert(self) -> str:
        table_name = self._model_class.get_table_name()
        columns = self._model_class.get_table_columns()
        columns_clause = ', '.join(columns)
        placeholders = ', '.join(':{}'.format(name) for name in columns)
        return f'INSERT INTO {table_name} ({columns_clause}) VALUES ({placeholders})'

    def select(self) -> SelectStatement:
        return select(self._model_class)

    def select_by_pk(self) -> SelectStatement:
        return self.select() + f' WHERE {self._where_pk()}'

    def update(self) -> str:
        table_name = self._model_class.get_table_name()
        primary_key = self._model_class.get_primary_key()
        columns = set(self._model_class.get_table_columns()) - set(primary_key)
        set_clause = ', '.join('{0} = :{0}'.format(name) for name in columns)
        return f'UPDATE {table_name} SET {set_clause} WHERE {self._where_pk()}'


@dataclass
class Model:
    _table_name_: t.ClassVar[t.Optional[str]] = None
    _primary_key_: t.ClassVar[t.Tuple[str, ...]] = ('id',)

    def as_dict(self) -> t.Dict[str, t.Any]:
        return {name: getattr(self, name) for name in self.get_table_columns()}

    def delete(self) -> None:
        id_ = self.get_id()

        if isinstance(id_, dict):
            params = id_
        else:
            if not isinstance(id_, (tuple, list)):
                id_ = (id_,)
            params = {name: value for name, value in zip(self.get_primary_key(), id_)}

        connection = self.get_connection()

        with connection.transaction():
            connection.execute(self.get_builder().delete(), params)

    @classmethod
    def find(cls, id_: PrimaryKey) -> 'Model':
        row = cls.get_or_none(id_)

        if row is None:
            raise ObjectNotFound(f'{cls.__name__} with ID {id_} not found.')

        return row

    @classmethod
    def get_or_none(cls, id_: PrimaryKey) -> t.Optional['Model']:
        if isinstance(id_, dict):
            params = id_
        else:
            if not isinstance(id_, (tuple, list)):
                id_ = (id_,)
            params = {name: value for name, value in zip(cls.get_primary_key(), id_)}

        row: t.Optional[Model] = cls.get_connection().query(
            cls.get_builder().select_by_pk(), params
        ).fetchone()

        return row

    @classmethod
    @lru_cache
    def get_builder(cls) -> SQLQueryBuilder:
        return SQLQueryBuilder(cls)

    @classmethod
    def get_connection(cls) -> Connection:
        raise NotImplementedError

    def get_id(self) -> t.Optional[PrimaryKey]:
        value = tuple(getattr(self, name) for name in self.get_primary_key())

        if not all(value):
            return None

        return value[0] if len(value) == 1 else value

    @classmethod
    def get_primary_key(cls) -> t.Tuple[str, ...]:
        return cls._primary_key_

    @classmethod
    @lru_cache
    def get_table_columns(cls) -> t.Tuple[str, ...]:
        return tuple(f.name for f in fields(cls) if not f.name.startswith('_'))

    @classmethod
    def get_table_name(cls) -> str:
        if cls._table_name_ is None:
            table_name = cls.__name__
            lst = re.findall(r'([A-Z][a-z0-9]+)', table_name) or [table_name]
            cls._table_name_ = '_'.join(w.lower() for w in lst)
        return cls._table_name_

    @classmethod
    def is_autoincrement_pk(cls) -> bool:
        pk = cls.get_primary_key()

        if len(pk) == 1:
            name = pk[0]
            hints = t.get_type_hints(cls)
            return int in t.get_args(hints[name])

        return False

    def save(self) -> None:
        connection = self.get_connection()
        is_empty_id = self.get_id() is None

        if not is_empty_id:
            with connection.transaction():
                result = connection.execute(self.get_builder().update(), self.as_dict())

                if result.cursor.rowcount > 0:
                    return None

        is_composite_pk = len(self.get_primary_key()) > 1

        if is_empty_id and (is_composite_pk or not self.is_autoincrement_pk()):
            raise ValueError('You must specify a value for the primary key.')

        with connection.transaction():
            result = connection.execute(self.get_builder().insert(), self.as_dict())

            if is_empty_id and self.is_autoincrement_pk():
                self.set_id(result.cursor.lastrowid)

    def set_id(self, id_: PrimaryKey) -> None:
        if isinstance(id_, dict):
            for name in self.get_primary_key():
                setattr(self, name, id_[name])
        else:
            if not isinstance(id_, (tuple, list)):
                id_ = (id_,)

            for name, value in zip(self.get_primary_key(), id_):
                setattr(self, name, value)
