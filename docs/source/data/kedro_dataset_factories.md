# Kedro dataset factories
You can load multiple datasets with similar configuration using dataset factories, introduced in Kedro 0.18.12.

The syntax allows you to generalise the configuration and reduce the number of similar catalog entries by matching datasets used in your project's pipelines to dataset factory patterns.

## Generalise datasets with similar names and types into one dataset factory
Consider the following catalog entries:

```yaml
factory_data:
  type: pandas.CSVDataSet
  filepath: data/01_raw/factory_data.csv


process_data:
  type: pandas.CSVDataSet
  filepath: data/01_raw/process_data.csv
```

The datasets in this catalog can be generalised to the following dataset factory:

```yaml
"{name}_data":
  type: pandas.CSVDataSet
  filepath: data/01_raw/{name}_data.csv
```

When `factory_data` or `process_data` is used in your pipeline, it is matched to the factory pattern `{name}_data`. The factory pattern must always be enclosed in
quotes to avoid YAML parsing errors.


## Generalise datasets of the same type into one dataset factory
You can also combine all the datasets with the same type and configuration details. For example, consider the following
catalog with three datasets named `boats`, `cars` and `planes` of the type `pandas.CSVDataSet`:

```yaml
boats:
  type: pandas.CSVDataSet
  filepath: data/01_raw/shuttles.csv

cars:
  type: pandas.CSVDataSet
  filepath: data/01_raw/reviews.csv

planes:
  type: pandas.CSVDataSet
  filepath: data/01_raw/companies.csv
```

These datasets can be combined into the following dataset factory:

```yaml
"{dataset_name}#csv":
  type: pandas.CSVDataSet
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
## Generalise datasets using namespaces into one dataset factory
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
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor_{namespace}.pkl
  versioned: true
```
## Generalise datasets of the same type in different layers into one dataset factory with multiple placeholders

You can use multiple placeholders in the same pattern. For example, consider the following catalog where the dataset
entries share `type`, `file_format` and `save_args`:

```yaml
processing.factory_data:
  type: spark.SparkDataSet
  filepath: data/processing/factory_data.pq
  file_format: parquet
  save_args:
    mode: overwrite

processing.process_data:
  type: spark.SparkDataSet
  filepath: data/processing/process_data.pq
  file_format: parquet
  save_args:
    mode: overwrite

modelling.metrics:
  type: spark.SparkDataSet
  filepath: data/modelling/factory_data.pq
  file_format: parquet
  save_args:
    mode: overwrite
```

This could be generalised to the following pattern:

```yaml
"{layer}.{dataset_name}":
  type: spark.SparkDataSet
  filepath: data/{layer}/{dataset_name}.pq
  file_format: parquet
  save_args:
    mode: overwrite
```
All the placeholders used in the catalog entry body must exist in the factory pattern name.

### Generalise datasets using multiple dataset factories
You can have multiple dataset factories in your catalog. For example:

```yaml
"{namespace}.{dataset_name}@spark":
  type: spark.SparkDataSet
  filepath: data/{namespace}/{dataset_name}.pq
  file_format: parquet

"{dataset_name}@csv":
  type: pandas.CSVDataSet
  filepath: data/01_raw/{dataset_name}.csv
```

Having multiple dataset factories in your catalog can lead to a situation where a dataset name from your pipeline might
match multiple patterns. To overcome this, Kedro sorts all the potential matches for the dataset name in the pipeline and picks the best match.
The matches are ranked according to the following criteria:

1. Number of exact character matches between the dataset name and the factory pattern. For example, a dataset named `factory_data$csv` would match `{dataset}_data$csv` over `{dataset_name}$csv`.
2. Number of placeholders. For example, the dataset `preprocessing.shuttles+csv` would match `{namespace}.{dataset}+csv` over `{dataset}+csv`.
3. Alphabetical order

### Generalise all datasets with a catch-all dataset factory to overwrite the default `MemoryDataSet`
You can use dataset factories to define a catch-all pattern which will overwrite the default `MemoryDataSet` creation.

```yaml
"{default_dataset}":
  type: pandas.CSVDataSet
  filepath: data/{default_dataset}.csv

```
Kedro will now treat all the datasets mentioned in your project's pipelines that do not appear as specific patterns or explicit entries in your catalog
as `pandas.CSVDataSet`.
