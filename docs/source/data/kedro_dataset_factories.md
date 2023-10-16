# Kedro dataset factories
You can load multiple datasets with similar configuration using dataset factories, introduced in Kedro 0.18.12.

The syntax allows you to generalise your configuration and reduce the number of similar catalog entries by matching datasets used in your project's pipelines to dataset factory patterns.

```{warning}
Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.
```

## How to generalise datasets with similar names and types

Consider the following catalog entries:

```yaml
factory_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/factory_data.csv


process_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/process_data.csv
```

The datasets in this catalog can be generalised to the following dataset factory:

```yaml
"{name}_data":
  type: pandas.CSVDataset
  filepath: data/01_raw/{name}_data.csv
```

When `factory_data` or `process_data` is used in your pipeline, it is matched to the factory pattern `{name}_data`. The factory pattern must always be enclosed in
quotes to avoid YAML parsing errors.


## How to generalise datasets of the same type

You can also combine all the datasets with the same type and configuration details. For example, consider the following
catalog with three datasets named `boats`, `cars` and `planes` of the type `pandas.CSVDataset`:

```yaml
boats:
  type: pandas.CSVDataset
  filepath: data/01_raw/shuttles.csv

cars:
  type: pandas.CSVDataset
  filepath: data/01_raw/reviews.csv

planes:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
```

These datasets can be combined into the following dataset factory:

```yaml
"{dataset_name}#csv":
  type: pandas.CSVDataset
  filepath: data/01_raw/{dataset_name}.csv
```

You will then have to update the pipelines in your project located at `src/<project_name>/<pipeline_name>/pipeline.py` to refer to these datasets as `boats#csv`,
`cars#csv` and `planes#csv`. Adding a suffix or a prefix to the dataset names and the dataset factory patterns, like `#csv` here, ensures that the dataset
names are matched with the intended pattern.

```python
from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preprocess_boats,
                inputs="boats#csv",
                outputs="preprocessed_boats",
                name="preprocess_boats_node",
            ),
            node(
                func=preprocess_cars,
                inputs="cars#csv",
                outputs="preprocessed_cars",
                name="preprocess_cars_node",
            ),
            node(
                func=preprocess_planes,
                inputs="planes#csv",
                outputs="preprocessed_planes",
                name="preprocess_planes_node",
            ),
            node(
                func=create_model_input_table,
                inputs=[
                    "preprocessed_boats",
                    "preprocessed_planes",
                    "preprocessed_cars",
                ],
                outputs="model_input_table",
                name="create_model_input_table_node",
            ),
        ]
    )
```
## How to generalise datasets using namespaces

You can also generalise the catalog entries for datasets belonging to namespaced modular pipelines. Consider the
following pipeline which takes in a `model_input_table` and outputs two regressors belonging to the
`active_modelling_pipeline` and the `candidate_modelling_pipeline` namespaces:

```python
from kedro.pipeline import Pipeline, node
from kedro.pipeline.modular_pipeline import pipeline

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs) -> Pipeline:
    pipeline_instance = pipeline(
        [
            node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "y_train"],
                name="split_data_node",
            ),
            node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
        ]
    )
    ds_pipeline_1 = pipeline(
        pipe=pipeline_instance,
        inputs="model_input_table",
        namespace="active_modelling_pipeline",
    )
    ds_pipeline_2 = pipeline(
        pipe=pipeline_instance,
        inputs="model_input_table",
        namespace="candidate_modelling_pipeline",
    )

    return ds_pipeline_1 + ds_pipeline_2
```
You can now have one dataset factory pattern in your catalog instead of two separate entries for `active_modelling_pipeline.regressor`
and `candidate_modelling_pipeline.regressor` as below:

```yaml
{namespace}.regressor:
  type: pickle.PickleDataset
  filepath: data/06_models/regressor_{namespace}.pkl
  versioned: true
```
## How to generalise datasets of the same type in different layers

You can use multiple placeholders in the same pattern. For example, consider the following catalog where the dataset
entries share `type`, `file_format` and `save_args`:

```yaml
processing.factory_data:
  type: spark.SparkDataset
  filepath: data/processing/factory_data.pq
  file_format: parquet
  save_args:
    mode: overwrite

processing.process_data:
  type: spark.SparkDataset
  filepath: data/processing/process_data.pq
  file_format: parquet
  save_args:
    mode: overwrite

modelling.metrics:
  type: spark.SparkDataset
  filepath: data/modelling/factory_data.pq
  file_format: parquet
  save_args:
    mode: overwrite
```

This could be generalised to the following pattern:

```yaml
"{layer}.{dataset_name}":
  type: spark.SparkDataset
  filepath: data/{layer}/{dataset_name}.pq
  file_format: parquet
  save_args:
    mode: overwrite
```
All the placeholders used in the catalog entry body must exist in the factory pattern name.

## How to generalise datasets using multiple dataset factories
You can have multiple dataset factories in your catalog. For example:

```yaml
"{namespace}.{dataset_name}@spark":
  type: spark.SparkDataset
  filepath: data/{namespace}/{dataset_name}.pq
  file_format: parquet

"{dataset_name}@csv":
  type: pandas.CSVDataset
  filepath: data/01_raw/{dataset_name}.csv
```

Having multiple dataset factories in your catalog can lead to a situation where a dataset name from your pipeline might
match multiple patterns. To overcome this, Kedro sorts all the potential matches for the dataset name in the pipeline and picks the best match.
The matches are ranked according to the following criteria:

1. Number of exact character matches between the dataset name and the factory pattern. For example, a dataset named `factory_data$csv` would match `{dataset}_data$csv` over `{dataset_name}$csv`.
2. Number of placeholders. For example, the dataset `preprocessing.shuttles+csv` would match `{namespace}.{dataset}+csv` over `{dataset}+csv`.
3. Alphabetical order

## How to override the default dataset creation with dataset factories

You can use dataset factories to define a catch-all pattern which will overwrite the default [`MemoryDataset`](/kedro.io.MemoryDataset) creation.

```yaml
"{default_dataset}":
  type: pandas.CSVDataset
  filepath: data/{default_dataset}.csv

```
Kedro will now treat all the datasets mentioned in your project's pipelines that do not appear as specific patterns or explicit entries in your catalog
as `pandas.CSVDataset`.

## CLI commands for dataset factories

To manage your dataset factories, two new commands have been added to the Kedro CLI: `kedro catalog rank` (0.18.12) and `kedro catalog resolve` (0.18.13).

### How to use `kedro catalog rank`

This command outputs a list of all dataset factories in the catalog, ranked in the order by which pipeline datasets are matched against them. The ordering is determined by the following criteria:

1. The number of non-placeholder characters in the pattern
2. The number of placeholders in the pattern
3. Alphabetic ordering

Consider a catalog file with the following patterns:

<details>
<summary><b>Click to expand</b></summary>

```yaml
"{layer}.{dataset_name}":
  type: pandas.CSVDataset
  filepath: data/{layer}/{dataset_name}.csv

preprocessed_{dataset_name}:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/preprocessed_{dataset_name}.pq

processed_{dataset_name}:
  type: pandas.ParquetDataset
  filepath: data/03_primary/processed_{dataset_name}.pq

"{dataset_name}_csv":
  type: pandas.CSVDataset
  filepath: data/03_primary/{dataset_name}.csv

"{namespace}.{dataset_name}_pq":
  type: pandas.ParquetDataset
  filepath: data/03_primary/{dataset_name}_{namespace}.pq

"{default_dataset}":
  type: pickle.PickleDataset
  filepath: data/01_raw/{default_dataset}.pickle
```
</details>

Running `kedro catalog rank` will result in the following output:

```
- preprocessed_{dataset_name}
- processed_{dataset_name}
- '{namespace}.{dataset_name}_pq'
- '{dataset_name}_csv'
- '{layer}.{dataset_name}'
- '{default_dataset}'
```

As we can see, the entries are ranked firstly by how many non-placeholders are in the pattern, in descending order. Where two entries have the same number of non-placeholder characters, `{namespace}.{dataset_name}_pq` and `{dataset_name}_csv` with four each, they are then ranked by the number of placeholders, also in decreasing order. `{default_dataset}` is the least specific pattern possible, and will always be matched against last.

### How to use `kedro catalog resolve`

This command resolves dataset patterns in the catalog against any explicit dataset entries in the project pipeline. The resulting output contains all explicit dataset entries in the catalog and any dataset in the default pipeline that resolves some dataset pattern.

To illustrate this, consider the following catalog file:

<details>
<summary><b>Click to expand</b></summary>

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv

reviews:
  type: pandas.CSVDataset
  filepath: data/01_raw/reviews.csv

shuttles:
  type: pandas.ExcelDataset
  filepath: data/01_raw/shuttles.xlsx
  load_args:
    engine: openpyxl # Use modern Excel engine, it is the default since Kedro 0.18.0

preprocessed_{name}:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/preprocessed_{name}.pq

"{default}":
  type: pandas.ParquetDataset
  filepath: data/03_primary/{default}.pq
```
</details>

and the following pipeline in `pipeline.py`:

<details>
<summary><b>Click to expand</b></summary>

```python
def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocess_companies_node",
            ),
            node(
                func=preprocess_shuttles,
                inputs="shuttles",
                outputs="preprocessed_shuttles",
                name="preprocess_shuttles_node",
            ),
            node(
                func=create_model_input_table,
                inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
                outputs="model_input_table",
                name="create_model_input_table_node",
            ),
        ]
    )
```
</details>

The resolved catalog output by the command will be as follows:

<details>
<summary><b>Click to expand</b></summary>

```yaml
companies:
  filepath: data/01_raw/companies.csv
  type: pandas.CSVDataset
model_input_table:
  filepath: data/03_primary/model_input_table.pq
  type: pandas.ParquetDataset
preprocessed_companies:
  filepath: data/02_intermediate/preprocessed_companies.pq
  type: pandas.ParquetDataset
preprocessed_shuttles:
  filepath: data/02_intermediate/preprocessed_shuttles.pq
  type: pandas.ParquetDataset
reviews:
  filepath: data/01_raw/reviews.csv
  type: pandas.CSVDataset
shuttles:
  filepath: data/01_raw/shuttles.xlsx
  load_args:
    engine: openpyxl
  type: pandas.ExcelDataset
```
</details>

By default this is output to the terminal. However, if you wish to output the resolved catalog to a specific file, you can use the redirection operator `>`:

```bash
kedro catalog resolve > output_file.yaml
```
