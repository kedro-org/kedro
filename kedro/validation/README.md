# Kedro Validation

`kedro.validation` contains two validation features:

1. **Dataset validation (KEP-7 v2, this branch)** — declare a validator on a catalog
   entry with the `validator:` key; the `DataCatalog` applies it on every load and save.
2. **Parameter validation (KEP-1)** — validates `params:` inputs against Pydantic
   models or dataclasses (`TypeExtractor`, `ParameterValidator`, `instantiate_model`).

## Quick start: the `validator:` key

```python
# src/<package>/schemas/companies.py
import pandera.pandas as pa

class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1)

    class Config:
        strict = False
        coerce = True
```

```yaml
# conf/base/catalog.yml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator: my_package.schemas.companies.CompaniesSchema
```

Every `catalog.load("companies")` now validates (and dtype-coerces) the DataFrame;
every `catalog.save(...)` validates **before** writing, so invalid data never lands on
disk. Failures raise `DataValidationError` with a bounded, grouped report:

```
Validation failed for dataset 'companies' on load
(validator: my_package.schemas.companies.CompaniesSchema)
2 check(s) failed — 3 failure case(s):
  - company_rating: greater_than_or_equal_to(0) — 2 cases (e.g. -0.5, -1.2)
  - id: field_uniqueness — 1 case (e.g. 10542)
```

The long form gives full control — see `examples/catalog.yml` for all recipes
(long form, YAML-anchor shared schemas, factory patterns, non-tabular validators):

```yaml
validator:
  class: my_package.schemas.reviews.ReviewsSchema
  on: [save]          # subset of [load, save]; default both
  severity: warn      # error (default) | warn
  options: {lazy: true, sample: 1000}   # forwarded to the adapter
```

Any object with a `validate(data) -> data` method (raising on failure) satisfies the
`Validator` protocol — pandera is just the built-in adapter, kept lazily imported and
optional. Opt out per catalog (`DataCatalog(..., validation_enabled=False)`) or
globally (`KEDRO_DATASET_VALIDATION=0`, which wins over the flag).

```python
from kedro.validation import validate_catalog_dataset

result = validate_catalog_dataset(catalog, "companies")   # never raises
result.status        # "passed" | "failed" | "skipped" | "errored"
result.to_dict()     # JSON-safe report; result.raise_if_failed() to escalate
```

## Package layout

| File | Role |
|---|---|
| `core.py` | `Validator` protocol, `ValidatorSpec`, `resolve_validator`, `CheckFailure`, `DataValidationError`, `ValidationConfigurationError`, `preflight_check` |
| `pandera_validator.py` | Pandera adapter (`pandera.pandas`/`polars`/`pyspark`, lazy error grouping) |
| `api.py` | `ValidationResult`, `validate_catalog_dataset`, `validate_catalog` |
| `type_extractor.py`, `parameter_validator.py`, `model_factory.py`, `exceptions.py`, `utils.py` | KEP-1 parameter validation (unchanged) |
| `dataset_validator.py` | Deprecated import shim (v1 wrapper removed) |

The catalog-side funnel lives in `kedro/io/data_catalog.py` (`_maybe_validate`,
`catalog.validators`); the reserved key constant is `VALIDATOR_KEY` in `kedro/io/core.py`.

## Learn more

- **Design:** [`KEP-7-dataset-validation-v2.md`](../../KEP-7-dataset-validation-v2.md) (repo root)
- **Runnable demo:** `python examples/demo_catalog_validation.py` (from repo root)
- **Example config:** [`examples/catalog.yml`](../../examples/catalog.yml)
