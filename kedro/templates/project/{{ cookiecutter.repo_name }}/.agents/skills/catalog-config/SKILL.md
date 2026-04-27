---
name: catalog-config
description: >-
  Kedro catalog configuration guidance for conf/**/*.yml files. Use when adding
  datasets, editing catalog entries, setting up factories, or working with
  credentials and parameter interpolation.
---
# Catalog Configuration

## Dataset type naming

Use the current module path:

```
kedro_datasets.<library>.<Type>Dataset
```

Short form also works — Kedro resolves `pandas.CSVDataset` automatically.

Two things agents get wrong:

- **Wrong module**: `kedro.extras.datasets.*` is deprecated and removed — never generate it.
- **Wrong casing**: since kedro-datasets 2.0, use lowercase `Dataset` (e.g. `CSVDataset`, not `CSVDataSet`).

## Check installed version

Before suggesting a dataset type or its arguments, run:

```bash
pip show kedro-datasets
```

Then refer to the docs for the installed version:
https://docs.kedro.org/projects/kedro-datasets

Do not guess constructor arguments from training data — they change across versions.

## load_args and save_args

Most dataset types accept `load_args` and `save_args` to pass options to the underlying library:

```yaml
my_dataset:
  type: pandas.CSVDataset
  filepath: data/01_raw/data.csv
  load_args:
    sep: ","
    encoding: utf-8
  save_args:
    index: false
```

The valid keys depend on the dataset type and its underlying library — check the docs for the installed version rather than guessing.

## Factory patterns

Use the `"{name}"` placeholder to create a single entry that matches multiple datasets:

```yaml
"{my_pattern}":
  type: kedro_datasets.pandas.CSVDataset
  filepath: data/01_raw/{my_pattern}.csv
```

The placeholder inside the quotes becomes a wildcard matched at runtime.

## Data directory structure

Place `filepath` values in the correct layer directory:

| Layer | Directory | Purpose |
|-------|-----------|---------|
| Raw | `data/01_raw/` | Original, immutable input data |
| Intermediate | `data/02_intermediate/` | Cleaned or pre-processed data |
| Primary | `data/03_primary/` | Domain-ready, analytics-ready data |
| Feature | `data/04_feature/` | Feature-engineered data |
| Model input | `data/05_model_input/` | Final data fed to models |
| Models | `data/06_models/` | Trained model artifacts |
| Model output | `data/07_model_output/` | Predictions and scores |
| Reporting | `data/08_reporting/` | Dashboards, plots, report tables |

## Credentials

Reference credentials by key — do not inline secrets:

```yaml
my_dataset:
  type: kedro_datasets.pandas.CSVDataset
  filepath: s3://bucket/path.csv
  credentials: my_credentials
```

The key (`my_credentials`) must match an entry in `conf/local/credentials.yml`.

## OmegaConf interpolation

Values can be injected at runtime: `${globals:key}` (from `conf/base/globals.yml`), `${runtime_params:key}` (from CLI `--params`), `${oc.env:VAR}` (environment variable).
