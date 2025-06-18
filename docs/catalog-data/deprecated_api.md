# Deprecated API

The following `DataCatalog` methods and CLI commands are deprecated and will be removed from Kedro version **`1.0`**.
Please update your code and workflows accordingly. Where possible, recommended alternatives are provided.

| Deprecated Item           | Type        | Replacement / Notes                                                |
| ------------------------- | ----------- | ------------------------------------------------------------------ |
| `catalog._get_dataset()`  | Method      | Internal use only; use `catalog.get()` instead                     |
| `catalog.add_all()`       | Method      | Prefer explicit catalog construction or use `catalog.add()`        |
| `catalog.add_feed_dict()` | Method      | Use `catalog["my_dataset"] = ...` (dict-style assignment)          |
| `catalog.list()`          | Method      | Replaced by `catalog.filter()`                                     |
| `catalog.shallow_copy()`  | Method      | Removed; no longer needed after internal refactor                  |
| `kedro catalog create`    | CLI Command | Removed; manual catalog entry creation no longer supported via CLI |
