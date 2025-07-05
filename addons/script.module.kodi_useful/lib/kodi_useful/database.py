from __future__ import annotations

from dataclasses import dataclass, fields
import datetime
from functools import cached_property, lru_cache, partial
import logging
import sqlite3
import re
import typing as t
from typing import Any, Dict, Tuple, Union

if t.TYPE_CHECKING:
    from types import TracebackType


__all__ = ('select', 'Connection', 'Model', 'SQLStatement')


PrimaryKey = Union[Any, Tuple[Any, ...], Dict[str, Any]]

logger = logging.getLogger(__name__)

sqlite3.register_adapter(datetime.date, lambda v: v.isoformat())
sqlite3.register_adapter(datetime.datetime, lambda v: v.isoformat())
# sqlite3.register_adapter(datetime, lambda v: int(v.timestamp()))

sqlite3.register_converter('date', lambda v: datetime.date.fromisoformat(v.decode()))
sqlite3.register_converter('datetime', lambda v: datetime.datetime.fromisoformat(v.decode()))
sqlite3.register_converter('timestamp', lambda v: datetime.datetime.fromtimestamp(int(v)))


def model_row_factory(
    cursor: sqlite3.Cursor,
    row: t.Tuple[t.Any, ...],
    model_class: t.Type[Model],
) -> Model:
    columns = [column[0] for column in cursor.description]
    return model_class(**{
        key: value
        for key, value in zip(columns, row)
    })


def select(model_class: t.Type[Model]) -> SelectStatement:
    table_name = model_class.get_table_name()
    columns = model_class.get_table_columns()
    columns_clause = ', '.join(columns)
    return SelectStatement(
        query=f'SELECT {columns_clause} FROM {table_name}',
        model_class=model_class,
    )


class Connection:
    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._conn: t.Optional[sqlite3.Connection] = None

    def __enter__(self) -> Connection:
        return self

    def __exit__(
        self,
        err_type: t.Optional[t.Type[BaseException]],
        err: t.Optional[BaseException],
        tb: TracebackType,
    ) -> None:
        self.commit() if err_type is None else self.rollback()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._filename, detect_types=sqlite3.PARSE_DECLTYPES)
            self._conn.row_factory = sqlite3.Row
            self._conn.set_trace_callback(logger.debug)
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    def execute(
        self,
        stmt: SQLStatement,
        **payload: t.Any,
    ) -> sqlite3.Cursor:
        stmt_placeholders = set(stmt.placeholders)
        passed_placeholders = set(payload.keys())

        missing_placeholders = stmt_placeholders - passed_placeholders

        if missing_placeholders:
            raise ValueError('Missing values for parameters: %s' % ', '.join(missing_placeholders))

        unknown_placeholders = passed_placeholders - stmt_placeholders

        if unknown_placeholders:
            raise ValueError('Unknown parameters passed: %s' % ', '.join(unknown_placeholders))

        data = tuple(payload[name] for name in stmt.placeholders)

        return self._get_connection().execute(str(stmt), data)

    def executescript(self, sql_script: str) -> sqlite3.Cursor:
        return self._get_connection().executescript(sql_script)

    def query(
        self,
        stmt: SelectStatement,
        model_class: t.Optional[t.Type[Model]] = None,
        **payload: t.Any,
    ) -> sqlite3.Cursor:
        cursor = self.execute(stmt, **payload)

        if model_class is None:
            model_class = stmt.model_class

        if model_class is not None:
            cursor.row_factory = partial(model_row_factory, model_class=model_class)

        return cursor

    def rollback(self) -> None:
        if self._conn is not None:
            self._conn.rollback()


class SQLStatement:
    def __init__(self, query: str) -> None:
        self.query = query

    def __repr__(self) -> str:
        return f'{type(self)}({self.query!r})'

    def __str__(self) -> str:
        return self.query

    def __add__(self, other: str) -> SQLStatement:
        if not isinstance(other, str):
            return NotImplemented
        return self.__class__('%s %s' % (self.query, other))

    @property
    @lru_cache
    def placeholders(self) -> t.Sequence[str]:
        clean_query = re.sub(r'(["\']).*?\1', '', self.query)
        return re.findall(r':(\w+)', clean_query)


class SelectStatement(SQLStatement):
    def __init__(
        self,
        query: str,
        model_class: t.Optional[t.Type[Model]] = None,
    ) -> None:
        super().__init__(query)
        self.model_class = model_class

    def __add__(self, other: str) -> SelectStatement:
        if not isinstance(other, str):
            return NotImplemented
        return self.__class__(
            query='%s %s' % (self.query, other),
            model_class=self.model_class,
        )

    def limit(self, value: int) -> SelectStatement:
        return self + 'LIMIT %d' % value

    def offset(self, value: int) -> SelectStatement:
        return self + 'OFFSET %d' % value

    def order_by(self, name: str, desc: bool = False) -> SelectStatement:
        direction = 'DESC' if desc else 'ASC'
        return self + ('ORDER BY %s %s' % (name, direction))


class SQLQueryBuilder:
    def __init__(self, model_class: t.Type[Model]) -> None:
        self._model_class = model_class

    def _where_pk(self) -> str:
        return ' AND '.join('{0} = :{0}'.format(name) for name in self._model_class.get_primary_key())

    def delete(self) -> SQLStatement:
        return SQLStatement(f'DELETE FROM {self._model_class.get_table_name()} WHERE {self._where_pk()}')

    def insert(self) -> SQLStatement:
        table_name = self._model_class.get_table_name()
        columns = self._model_class.get_table_columns()
        columns_clause = ', '.join(columns)
        placeholders = ', '.join(':{}'.format(name) for name in columns)
        return SQLStatement(f'INSERT INTO {table_name} ({columns_clause}) VALUES ({placeholders})')

    def select(self) -> SelectStatement:
        return select(self._model_class)

    def select_by_pk(self) -> SelectStatement:
        return self.select() + f'WHERE {self._where_pk()}'

    def update(self) -> SQLStatement:
        table_name = self._model_class.get_table_name()
        primary_key = self._model_class.get_primary_key()
        columns = set(self._model_class.get_table_columns()) - set(primary_key)
        set_clause = ', '.join('{0} = :{0}'.format(name) for name in columns)
        return SQLStatement(f'UPDATE {table_name} SET {set_clause} WHERE {self._where_pk()}')


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

        with self.get_connection() as connection:
            connection.execute(self.get_builder().delete(), **params)

    @classmethod
    def find(cls, id_: PrimaryKey) -> t.Optional[Model]:
        if isinstance(id_, dict):
            params = id_
        else:
            if not isinstance(id_, (tuple, list)):
                id_ = (id_,)
            params = {name: value for name, value in zip(cls.get_primary_key(), id_)}

        row: t.Optional[Model] = cls.get_connection().query(
            cls.get_builder().select_by_pk(), model_class=cls, **params
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
        is_empty_id = self.get_id() is None

        if not is_empty_id:
            with self.get_connection() as connection:
                cursor = connection.execute(self.get_builder().update(), **self.as_dict())

                if cursor.rowcount > 0:
                    return None

        is_composite_pk = len(self.get_primary_key()) > 1

        if is_empty_id and (is_composite_pk or not self.is_autoincrement_pk()):
            raise ValueError('You must specify a value for the primary key.')

        with self.get_connection() as connection:
            cursor = connection.execute(self.get_builder().insert(), **self.as_dict())

            if is_empty_id and self.is_autoincrement_pk():
                self.set_id(cursor.lastrowid)

    def set_id(self, id_: PrimaryKey) -> None:
        if isinstance(id_, dict):
            for name in self.get_primary_key():
                setattr(self, name, id_[name])
        else:
            if not isinstance(id_, (tuple, list)):
                id_ = (id_,)

            for name, value in zip(self.get_primary_key(), id_):
                setattr(self, name, value)
