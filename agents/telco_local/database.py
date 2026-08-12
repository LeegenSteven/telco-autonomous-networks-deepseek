from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import duckdb

from telco_local.settings import settings


class Record(dict):
    """Dictionary row that also supports the attribute access used by the agents."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


@contextmanager
def connection(*, require_initialized: bool = True) -> Iterator[duckdb.DuckDBPyConnection]:
    database_path = settings.database_path
    if require_initialized and not database_path.exists():
        raise RuntimeError(
            f"Local database not found at {database_path}. Run "
            "`python -m telco_local.init_db` from the agents directory."
        )
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(database_path))
    try:
        yield conn
    finally:
        conn.close()


def execute_query(
    query: str,
    parameters: Sequence[Any] | None = None,
) -> list[Record]:
    with connection() as conn:
        cursor = conn.execute(query, parameters or [])
        if not cursor.description:
            return []
        columns = [column[0] for column in cursor.description]
        return [Record(zip(columns, row)) for row in cursor.fetchall()]


def execute_statement(
    statement: str,
    parameters: Sequence[Any] | None = None,
) -> None:
    with connection() as conn:
        conn.execute(statement, parameters or [])


def database_exists() -> bool:
    return Path(settings.database_path).exists()
