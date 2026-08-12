"""Local database helpers used by RCA tools."""

from telco_local.database import execute_query, execute_statement

INCIDENTS_TABLE = "incidents"
CELL_TRACES_TABLE = "cell_traces"

__all__ = [
    "CELL_TRACES_TABLE",
    "INCIDENTS_TABLE",
    "execute_query",
    "execute_statement",
]
