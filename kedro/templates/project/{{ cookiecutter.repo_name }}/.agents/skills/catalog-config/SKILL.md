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

Three things agents get wrong:

- **Wrong module**: `kedro.extras.datasets.*` is deprecated and removed — never generate it.
- **Wrong casing**: since kedro-datasets 2.0, use lowercase `Dataset` (e.g. `CSVDataset`, not `CSVDataSet`).
- **Top-level `layer:`**: deprecated since Kedro 0.19 and silently ignored. Use `metadata.kedro-viz.layer` instead:

  ```yaml
  companies:
    type: pandas.CSVDataset
    filepath: data/01_raw/companies.csv
    metadata:
      kedro-viz:
        layer: raw
  ```

## Check the docs before writing an entry

Do not guess constructor arguments from training data — they change across versions. You MUST look up the dataset type docs before writing the catalog entry.

**Step 1** — Get the installed version:

```bash
pip show kedro-datasets
```

If not installed, fall back to `stable` in the URL below.

**Step 2** — Fetch the docs page for the specific dataset type:

```
https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-{version}/api/kedro_datasets/{module}.{ClassName}/
```

For experimental datasets:

```
https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-{version}/api/kedro_datasets_experimental/{module}.{ClassName}/
```

Replace `{version}` with the installed version (e.g. `9.3.0`) or `stable`. Replace `{module}.{ClassName}` with the dataset type (e.g. `pandas.CSVDataset`, `polars.PolarsDatabaseDataset`).

**Step 3** — Read the constructor parameters from the docs page, then write the catalog entry using only documented arguments.

## Dependencies

When adding a dataset, ensure the required package is in `requirements.txt` (or `pyproject.toml`). Dataset types are shipped as extras of `kedro-datasets`:

```
kedro-datasets[pandas.CSVDataset]
```

For experimental types, the package is `kedro-datasets-experimental`:

```
kedro-datasets-experimental[polars.PolarsDatabaseDataset]
```

Suggest updating requirements when adding a new dataset type.

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

The placeholder inside the quotes becomes a wildcard matched at runtime. For advanced patterns (multiple placeholders, specificity ordering, partial matches), refer to: https://docs.kedro.org/en/stable/catalog-data/kedro_dataset_factories/

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

**Never** create or edit credential files under `conf/base/` — that directory is version-controlled and secrets would be committed. Credentials belong **exclusively** in `conf/local/credentials.yml`, which is gitignored by the project template.

For advanced credential patterns (nested `client_kwargs`, S3, SQL connection strings, per-environment overrides), refer to: https://docs.kedro.org/en/stable/catalog-data/data_catalog_yaml_examples/

## OmegaConf interpolation

Values can be injected at runtime: `${globals:key}` (from `conf/base/globals.yml`), `${runtime_params:key}` (from CLI `--params`), `${oc.env:VAR}` (environment variable). For advanced configuration patterns, refer to: https://docs.kedro.org/en/stable/configure/advanced_configuration/
