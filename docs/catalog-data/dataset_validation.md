# Dataset validation

Kedro can check the data behind a catalog entry every time it is loaded or saved. You declare a validator on the dataset in `catalog.yml`, and the `DataCatalog` enforces it wherever you use the catalog: in pipeline runs, in notebooks, in `kedro ipython`, and in CI. Invalid inputs are rejected before a node sees them, and invalid outputs are rejected before they reach storage.

This page shows you how to declare validators, how to control when they run, how to write your own, and how to validate datasets on demand from your own code.

## Quickstart with Pandera

To follow along, install Kedro with the Pandera extra for your dataframe library:

```bash
pip install "kedro[pandera-pandas]"   # or kedro[pandera-polars]
```

First, define a schema for your dataset as a plain [Pandera](https://pandera.readthedocs.io/) `DataFrameModel`. There is nothing Kedro-specific in this file, so if you already use Pandera, you can reuse the schemas you have:

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

Next, declare the schema on the dataset with the `validator` key:

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator: my_project.schemas.CompaniesSchema
```

After the validator is in your catalog, your nodes stay the same. Kedro validates the data whenever it passes through the catalog: when a `kedro run` loads the dataset, when you call `catalog.load("companies")` in a notebook, or when a node's output is saved. If the data does not match the schema, the operation fails and you'll see one error message listing all the failed checks:

```text
DataValidationError: Validation failed for dataset 'companies' on load
(validator: my_project.schemas.CompaniesSchema)
2 check(s) failed — 3 failure case(s):
  - id: field_uniqueness — 2 cases (e.g. 3888, 3888)
  - company_rating: greater_than_or_equal_to(0) — 1 case (e.g. -0.5)
```

The error groups the failures by check and shows a sample of the failing values. In most cases that is enough to see what went wrong without leaving the terminal. The message stays the same size for a ten-row frame or a ten-million-row frame.

When you need the complete picture, catch the error and inspect it. The `failures` attribute holds every check as a structured `CheckFailure` object, and `__cause__` carries the untouched backend report — for Pandera, the original `SchemaErrors` with its full `failure_cases` frame:

```python
from kedro.validation import DataValidationError

try:
    df = catalog.load("companies")
except DataValidationError as err:
    print(err.failures)  # structured, grouped failures
    print(err.__cause__.failure_cases)  # the full Pandera report
```

## The long form

The shorthand string covers most cases. When you need per-dataset control, use the long form:

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

For Pandera schemas, `options` takes the keyword arguments of Kedro's `PanderaValidator`. For example, `lazy` collects every failure before reporting instead of stopping at the first, and `head` limits validation to the start of a large dataset.

!!! tip

    Adopting validation on an existing project? Start with `severity: warn`. Failures are logged instead of raised, so you can see what would break before you enforce anything.

## Switching validation off

You can switch validation off at three levels, from narrowest to broadest:

- **Per dataset:** set `enabled: false` on the declaration, or `severity: warn` to observe without blocking.
- **Per project:** set `DATASET_VALIDATION = False` in `settings.py`. When you build a catalog yourself, `DataCatalog.from_config(..., validation_enabled=False)` does the same.
- **Per run:** the `KEDRO_DATASET_VALIDATION` environment variable overrides everything in both directions, with no code or config change. This is useful as an emergency switch when a validator gets in your way mid-incident:

```bash
KEDRO_DATASET_VALIDATION=0 kedro run
```

## Writing your own validator

Pandera is the reference backend, but the contract a validator has to meet is small: take data, return data, raise if the data is wrong. Anything that fits works, including validators for data that is not a dataframe at all — dictionaries, model artifacts, or plain text.

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

A plain function also works, declared by its dotted path. If your function returns `None`, the original data passes through unchanged. If it returns data, the returned value is what the pipeline receives, so validators can coerce data as well as check it.

!!! warning

    A validator class's `validate` method must **return the data**. If it returns `None`, the node receives `None`. Only plain functions get the assertion-style treatment where `None` means "pass the original through".

Whatever your validator raises is treated as a validation failure and reported as a `DataValidationError`. Both `DataValidationError` and `ValidationConfigurationError` subclass `DatasetError`, so any error handling you already have around catalog operations keeps working. Catch `DataValidationError` first when you want to treat schema failures separately from I/O failures.

## Validating on demand

During a `kedro run`, a failed validation stops the pipeline and raises an error. When you want to check datasets from your own code instead — in a script, a test, or a CI job — use `validate_dataset` and `validate_catalog`. These functions never raise for validation outcomes. Each call returns a `ValidationResult` with a `status` of `passed`, `failed`, `skipped`, or `errored`:

```python
from kedro.validation import validate_catalog, validate_dataset

result = validate_dataset(catalog, "companies")
result.status  # "passed", "failed", "skipped" or "errored"
result.failures  # structured check failures
result.to_dict()  # JSON-safe summary
result.raise_if_failed()  # opt back in to exceptions

results = validate_catalog(catalog)  # every dataset with a declared validator
```

Explicit calls always validate: the `enabled` flags and the kill switch are ignored, because asking is opting in. Pass `data=` to validate in-memory data without touching storage, and `on="save"` to check data against a save-mode declaration before you write it.

## Current scope

- One validator per dataset. Support for multiple validators per dataset might be added in a future release.
- pandas and Polars are the supported Pandera backends. Pandera's PySpark backend reports failures differently, and support for it is experimental.
- Validators on [dataset factory](kedro_dataset_factories.md) entries are captured when the dataset is first materialised.
