# Inspect a Kedro project

The inspection API lets you read the structure of a Kedro project without running it. It returns a [`ProjectSnapshot`][kedro.inspection.models.ProjectSnapshot] that captures:

- Project metadata (name, package, Kedro version)
- All registered pipelines and their nodes in topological order
- Catalog dataset configurations
- Parameter key names (not values)

# When to use the inspection API

Use `get_project_snapshot` when you need to read the structure of a Kedro project from Python code without running any nodes or loading any data. Common use cases include:

- **CI validation**: assert that expected pipelines, datasets, or parameters are present before a run
- **Tooling**: generate documentation, diagrams, or reports from project structure
- **IDE integrations**: surface pipeline metadata to developers without executing code
- **Programmatic access**: query project structure in scripts or notebooks

!!! note
    The inspection API reads configuration and pipeline definitions. It does not load datasets, execute nodes, or write data.

The following sections explain how to use the inspection API:

- [How to get a project snapshot](#how-to-get-a-project-snapshot)
- [How to access project metadata](#how-to-access-project-metadata)
- [How to explore pipeline structure](#how-to-explore-pipeline-structure)
- [How to inspect catalog datasets](#how-to-inspect-catalog-datasets)
- [How to list parameter keys](#how-to-list-parameter-keys)
- [How to inspect a specific environment](#how-to-inspect-a-specific-environment)

## How to get a project snapshot

Call [`get_project_snapshot`][kedro.inspection.get_project_snapshot] with the path to your project root — the directory that contains `pyproject.toml`:

```python
from kedro.inspection import get_project_snapshot

snapshot = get_project_snapshot("/path/to/my_project")
```

You can also pass a `Path` object or a relative path:

```python
from pathlib import Path
from kedro.inspection import get_project_snapshot

snapshot = get_project_snapshot(Path.cwd())
```

The returned [`ProjectSnapshot`][kedro.inspection.models.ProjectSnapshot] is a data class with four attributes: `metadata`, `pipelines`, `datasets`, and `parameters`.

## How to access project metadata

The `metadata` attribute is a [`ProjectMetadataSnapshot`][kedro.inspection.models.ProjectMetadataSnapshot] with the project name, Python package name, and the Kedro version declared in `pyproject.toml`:

```python
print(snapshot.metadata.project_name)   # "My Project"
print(snapshot.metadata.package_name)   # "my_project"
print(snapshot.metadata.kedro_version)  # "1.0.0"
```

## How to explore pipeline structure

The `pipelines` attribute is a list of [`PipelineSnapshot`][kedro.inspection.models.PipelineSnapshot] objects, one per registered pipeline. Each snapshot exposes the pipeline name, its nodes in topological order, and its free inputs and outputs:

```python
for pipeline in snapshot.pipelines:
    print(pipeline.name)
    print("  inputs: ", pipeline.inputs)
    print("  outputs:", pipeline.outputs)
    print("  nodes:  ", len(pipeline.nodes))
```

The output looks as follows:

```console
__default__
  inputs:  ['example_iris_data', 'params:example_learning_rate', ...]
  outputs: ['example_predictions']
  nodes:   4
data_engineering
  ...
```

To inspect the nodes within a specific pipeline:

```python
default_pipeline = next(p for p in snapshot.pipelines if p.name == "__default__")

for node in default_pipeline.nodes:
    print(node.name)
    print("  namespace:", node.namespace)
    print("  inputs:   ", node.inputs)
    print("  outputs:  ", node.outputs)
    print("  tags:     ", node.tags)
```

Each node is represented as a [`NodeSnapshot`][kedro.inspection.models.NodeSnapshot] with `name`, `namespace`, `inputs`, `outputs`, and `tags` fields.

## How to inspect catalog datasets

The `datasets` attribute is a dictionary mapping dataset names to [`DatasetSnapshot`][kedro.inspection.models.DatasetSnapshot] objects. Each snapshot contains the dataset type and, where present, its file path:

```python
for name, dataset in snapshot.datasets.items():
    print(f"{name}: {dataset.type}")
    if dataset.filepath:
        print(f"  filepath: {dataset.filepath}")
```

The output looks as follows:

```console
example_iris_data: pandas.CSVDataset
  filepath: data/01_raw/iris.csv
example_model: pickle.PickleDataset
  filepath: data/06_models/example_model.pkl
example_predictions: pickle.PickleDataset
  filepath: data/07_model_output/example_predictions.pkl
```

To look up a specific dataset by name:

```python
iris = snapshot.datasets["example_iris_data"]
print(iris.type)      # "pandas.CSVDataset"
print(iris.filepath)  # "data/01_raw/iris.csv"
```

!!! note
    Datasets resolved from [dataset factory patterns](../catalog-data/kedro_dataset_factories.md) are included in the snapshot. Datasets that appear as node inputs or outputs but have no catalog entry are not included.

## How to list parameter keys

The `parameters` attribute is a sorted list of parameter key strings.Parameter values are not stored

```python
print(snapshot.parameters)
# ['example_learning_rate', 'example_num_train_iter', 'example_test_data_ratio']
```

To check whether a specific parameter is configured:

```python
if "example_learning_rate" in snapshot.parameters:
    print("learning rate is configured")
```

## How to inspect a specific environment

By default, `get_project_snapshot` uses the project's default run environment (`local` overlaid on `base`). Pass the `env` argument to load configuration from a different environment:

```python
snapshot = get_project_snapshot(project_path = "/path/to/my_project", env="staging")
```

This follows the same environment resolution rules as `kedro run --env staging`. See [Configuration basics](../configure/configuration_basics.md) for details on how environments work.
