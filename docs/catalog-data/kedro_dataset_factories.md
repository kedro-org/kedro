# Kedro dataset factories

You can load multiple datasets with similar configuration using dataset factories, introduced in Kedro `0.18.12`. This page explains what dataset factories are and how Kedro resolves them. For step-by-step recipes, see [how to use dataset factories](how_to_use_dataset_factories.md).

!!! warning
    Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
    From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.

Dataset factories introduce a syntax that lets you generalise your configuration and reduce the number of similar catalog entries. They match datasets used in your project's pipelines to dataset factory patterns.

For example:

```yaml
factory_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/factory_data.csv

process_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/process_data.csv
```

With a dataset factory, both entries can be re-written as:

```yaml
"{name}_data":
  type: pandas.CSVDataset
  filepath: data/01_raw/{name}_data.csv
```

At runtime, the pattern is matched against the name of the datasets defined as node `inputs` or `outputs`:

```python
Node(
    func=process_factory,
    inputs="factory_data",
    outputs="process_data",
),

...
```

!!! note
    The factory pattern must always be enclosed in quotes to avoid YAML parsing errors.

Dataset factories behave like a **regular expression** and you can think of the syntax as a reversed `f-string`. In this case, the name of the input dataset `factory_data` matches the pattern `{name}_data` with the `_data` suffix, so it resolves `name` to `factory`. Likewise, it resolves `name` to `process` for the output dataset `process_data`.

This allows you to use one dataset factory pattern to replace multiple dataset entries. It keeps your catalog concise and lets you generalise datasets by name, type, or namespace.

## Types of patterns

The catalog supports three types of factory patterns:

1. Dataset patterns
2. User catch-all pattern
3. Default runtime patterns

**Dataset patterns**

Dataset patterns are defined explicitly in the `catalog.yml` using placeholders such as `{name}_data`.

```yaml
"{name}_data":
  type: pandas.CSVDataset
  filepath: data/01_raw/{name}_data.csv
```

This allows any dataset named `something_data` to be dynamically resolved using the pattern.

**User catch-all pattern**

A user catch-all pattern acts as a fallback when no dataset patterns match. It also uses a placeholder like `{default_dataset}`.

```yaml
"{default_dataset}":
  type: pandas.CSVDataset
  filepath: data/{default_dataset}.csv
```

!!! note
    A single user catch-all pattern is allowed per catalog. If more are specified, Kedro raises a `DatasetError`.

**Default runtime patterns**

Default runtime patterns are built-in patterns used by Kedro when datasets are not defined in the catalog, often for intermediate datasets generated during a pipeline run. They are defined per catalog type:

```python
# For DataCatalog
default_runtime_patterns: ClassVar = {
    "{default}": {"type": "kedro.io.MemoryDataset"}
}

# For SharedMemoryDataCatalog
default_runtime_patterns: ClassVar = {
    "{default}": {"type": "kedro.io.SharedMemoryDataset"}
}
```

These patterns enable automatic creation of in-memory or shared-memory datasets during execution.

## Patterns resolution order

When the `DataCatalog` is initialised, it scans the configuration to extract and validate any dataset patterns and the user catch-all pattern.

When resolving a dataset name, Kedro uses the following order of precedence:

1. **Dataset patterns:** Specific patterns defined in the `catalog.yml`. These are the most explicit and are matched first.

2. **User catch-all pattern:** A general fallback pattern (for example, `{default_dataset}`) that is matched if no dataset patterns apply. A single user catch-all pattern is allowed. Multiple patterns raise a `DatasetError`.

3. **Default runtime patterns:** Internal fallback behaviour provided by Kedro. These patterns are built into the catalog and automatically used at runtime to create datasets (for example, `MemoryDataset` or `SharedMemoryDataset`) when none of the above match.

### Default vs runtime behaviour

- **Default behaviour:** `DataCatalog` resolves dataset patterns and user catch-all patterns.
- **Runtime behaviour** (for example, during `kedro run`): default runtime patterns are automatically enabled to resolve intermediate datasets not defined in `catalog.yml`.

By default, runtime patterns are not used when calling `catalog.get()` unless explicitly enabled using the `fallback_to_runtime_pattern=True` flag.

!!! note
    Enabling `fallback_to_runtime_pattern=True` is recommended for advanced users with specific use cases. In most scenarios, Kedro handles it automatically during runtime.

For worked examples of resolution and ranking when multiple patterns could match, see [how dataset factory resolution works in practice](how_to_use_dataset_factories.md#how-dataset-factory-resolution-works-in-practice).

## Pipeline-aware catalog commands

The `DataCatalog` exposes a small set of pipeline-aware commands that inspect how datasets are resolved against factory patterns, available through both the CLI and interactive environments:

- `kedro catalog describe-datasets` — describes datasets used in a pipeline, grouped by how they were resolved (explicit entries, factory matches, default fallbacks).
- `kedro catalog list-patterns` — lists all dataset factory patterns defined in the catalog, ordered by priority.
- `kedro catalog resolve-patterns` — resolves datasets used in a pipeline against all dataset patterns, returning their full catalog configuration.

These commands are implemented by `CatalogCommandsMixin`, which Kedro composes into the catalog automatically when initialising a session. You don't need to do anything to use them through the CLI or in interactive environments like IPython and Jupyter. For programmatic access outside a Kedro session, see [how to access pipeline-aware catalog commands in code](how_to_use_dataset_factories.md#how-to-access-pipeline-aware-catalog-commands-in-code).

## How to override the default dataset creation with dataset factories

This procedural content has moved. See [how to override the default dataset creation with dataset factories](how_to_use_dataset_factories.md#how-to-override-the-default-dataset-creation-with-dataset-factories) on the dataset factories how-to page.
