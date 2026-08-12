from __future__ import annotations

import argparse
from pathlib import Path

from telco_local.database import connection
from telco_local.settings import REPOSITORY_ROOT, settings


PERFORMANCE_CSV = REPOSITORY_ROOT / "data" / "performance.csv"
CELL_TRACES_CSV = REPOSITORY_ROOT / "data" / "cell-traces.csv"
SCHEMA_SQL = Path(__file__).with_name("schema.sql")


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = ?
        """,
        [table_name],
    ).fetchone()
    return bool(row and row[0])


def _load_csv_table(conn, table_name: str, source: Path) -> None:
    conn.execute(
        f"""
        CREATE TABLE {table_name} AS
        SELECT * FROM read_csv(
            ?,
            header = true,
            auto_detect = true,
            timestampformat = '%m/%d/%Y %H:%M:%S',
            sample_size = -1,
            ignore_errors = false
        )
        """,
        [str(source)],
    )


def initialize_database(*, reset: bool = False) -> Path:
    for source in (PERFORMANCE_CSV, CELL_TRACES_CSV, SCHEMA_SQL):
        if not source.exists():
            raise FileNotFoundError(source)

    with connection(require_initialized=False) as conn:
        if reset:
            conn.execute("DROP VIEW IF EXISTS performance_kpi")
            conn.execute("DROP TABLE IF EXISTS performance")
            conn.execute("DROP TABLE IF EXISTS cell_traces")
            conn.execute("DROP TABLE IF EXISTS incidents")
            conn.execute("DROP TABLE IF EXISTS agent_events")

        if not _table_exists(conn, "performance"):
            _load_csv_table(conn, "performance", PERFORMANCE_CSV)
        if not _table_exists(conn, "cell_traces"):
            _load_csv_table(conn, "cell_traces", CELL_TRACES_CSV)

        conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

        performance_count = conn.execute(
            "SELECT COUNT(*) FROM performance"
        ).fetchone()[0]
        trace_count = conn.execute("SELECT COUNT(*) FROM cell_traces").fetchone()[0]

    print(f"Local database: {settings.database_path}")
    print(f"Performance rows: {performance_count}")
    print(f"Cell trace rows: {trace_count}")
    return settings.database_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the local telco DuckDB")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Recreate all local tables and remove existing incidents",
    )
    args = parser.parse_args()
    initialize_database(reset=args.reset)


if __name__ == "__main__":
    main()
