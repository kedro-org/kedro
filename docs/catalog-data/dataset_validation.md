# Dataset validation

Kedro can validate the data behind a catalog entry every time it is loaded or saved. You declare a validator on the dataset in `catalog.yml`, and the `DataCatalog` enforces it wherever the catalog is used: pipeline runs, notebooks, `kedro ipython` and CI. Invalid inputs are rejected before a node sees them, and invalid outputs are rejected before they reach storage.

## Quickstart with Pandera

Install Kedro with the Pandera extra for your dataframe library:

```bash
pip install "kedro[pandera-pandas]"   # or kedro[pandera-polars]
```

Define a schema as a plain [Pandera](https://pandera.readthedocs.io/) `DataFrameModel`:

```python
# src/my_project/schemas.py
import pandera.pandas as pa


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1, nullable=True)

    class Config:
        strict = False  # extra columns allowed
        coerce = True
```

Declare it on the dataset with the `validator` key:

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator: my_project.schemas.CompaniesSchema
```

That is the whole setup. Nodes do not change. When the data breaks the contract, the load or save fails, and the error reports every failed check in one message:

```text
DataValidationError: Validation failed for dataset 'companies' on load
(validator: my_project.schemas.CompaniesSchema)
2 check(s) failed — 3 failure case(s):
  - id: field_uniqueness — 2 cases (e.g. 3888, 3888)
  - company_rating: greater_than_or_equal_to(0) — 1 case (e.g. -0.5)
```

The rendered message stays the same size for a ten-row frame or a ten-million-row frame. The full backend report is available on the exception's `__cause__`, and the structured failures on its `failures` attribute.

## The long form

The shorthand string covers most cases. The long form gives you per-dataset control:

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator:
    class: my_project.schemas.CompaniesSchema
    on: [load, save] # validate on load, save, or both (default: both)
    severity: error # error (raise) or warn (log and continue)
    enabled: true # switch this validator off without deleting it
    skip_load_after_save: false # skip load validation right after a validated save
    options: # keyword arguments for the validator
      lazy: true
```

For Pandera validators, `options` accepts `lazy`, `head`, `tail`, `sample` and `random_state`.

!!! tip

    Adopting validation on an existing project? Start with `severity: warn`. Failures are logged instead of raised, so you can see what would break before enforcing anything.

## Switching validation off

Three levels, from narrowest to broadest:

- **Per dataset:** `enabled: false` on the declaration, or `severity: warn` to observe without blocking.
- **Per project:** set `DATASET_VALIDATION = False` in `settings.py`. When you build a catalog yourself, `DataCatalog.from_config(..., validation_enabled=False)` does the same.
- **Per run:** the `KEDRO_DATASET_VALIDATION` environment variable overrides everything in both directions, with no code or config change:

```bash
KEDRO_DATASET_VALIDATION=0 kedro run
```

## Writing your own validator

Pandera is the reference backend, but the contract is small: take data, return data, raise if it is wrong. Anything that fits works, including validators for non-tabular data.

A class with a `validate` method receives `options` as constructor arguments:

```python
# src/my_project/validators.py
class MinRows:
    def __init__(self, minimum=1):
        self.minimum = minimum

    def validate(self, data):
        if len(data) < self.minimum:
            raise ValueError(f"expected at least {self.minimum} rows, got {len(data)}")
        return data
```

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator:
    class: my_project.validators.MinRows
    options:
      minimum: 100
```

A plain function also works, declared by its dotted path. If it returns `None`, the original data passes through unchanged; if it returns data, the returned value is what the pipeline receives, so validators can coerce as well as check.

!!! warning

    A validator class's `validate` method must **return the data**. If it returns `None`, the node receives `None`. Only plain functions get the assertion-style treatment where `None` means "pass the original through".

Whatever the validator raises is treated as a validation failure and reported as a `DataValidationError`. Both `DataValidationError` and `ValidationConfigurationError` subclass `DatasetError`, so existing error handling around catalog operations keeps working; catch `DataValidationError` first to treat schema failures separately.

## Validating on demand

To check datasets without going through a load or save — in tooling, tests, or CI — use the on-demand API. It never raises for validation outcomes; every outcome is a `ValidationResult`:

```python
from kedro.validation import validate_catalog, validate_dataset

result = validate_dataset(catalog, "companies")
result.status  # "passed", "failed", "skipped" or "errored"
result.failures  # structured check failures
result.to_dict()  # JSON-safe summary
result.raise_if_failed()  # opt back in to exceptions

results = validate_catalog(catalog)  # every dataset with a declared validator
```

Explicit calls always validate, ignoring the `enabled` flags and the kill switch — asking is opting in. Pass `data=` to validate in-memory data without touching storage, and `on="save"` to check against a save-mode declaration.

## Current scope

- One validator per dataset. The list form is reserved for future use.
- pandas and Polars are the supported Pandera backends. Pandera's PySpark backend reports failures differently, and support for it is experimental.
- Validators on [dataset factory](kedro_dataset_factories.md) entries are captured when the dataset is first materialised.
