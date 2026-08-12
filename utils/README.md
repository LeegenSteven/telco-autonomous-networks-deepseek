# Utilities for local data processing

`csv2json.py` converts CSV input to JSON Lines. The local DeepSeek runtime does
not require this conversion because DuckDB reads the source CSV files directly.
