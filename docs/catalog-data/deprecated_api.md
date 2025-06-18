# Deprecated API

The following `DataCatalog` methods and CLI commands are deprecated and will be removed from Kedro version **`1.0`**.
Please update your code and workflows accordingly. Where possible, recommended alternatives are provided.

- `catalog._get_dataset()` – Internal method; no longer needed. Use `catalog.get()` instead.
- `catalog.add_all()` – Prefer explicit catalog construction or use `catalog.add()` if necessary.
- `catalog.add_feed_dict()` – Deprecated. Use dict-style assignment with `__setitem__()` instead (e.g., `catalog["my_dataset"] = ...`).
- `catalog.list()` – Replaced by `catalog.filter()`.
- `catalog.shallow_copy()` – Removed due to internal catalog refactoring; no replacement needed.
- `kedro catalog create` – The CLI command for creating catalog entries has been removed.
