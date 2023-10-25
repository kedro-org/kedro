# Advanced: Partitioned and incremental datasets

## Partitioned datasets

Distributed systems play an increasingly important role in ETL data pipelines. They increase the processing throughput, enabling us to work with much larger volumes of input data. A situation may arise where your Kedro node needs to read the data from a directory full of uniform files of the same type like JSON or CSV. Tools like `PySpark` and the corresponding [SparkDataset](/kedro_datasets.spark.SparkDataset) cater for such use cases but may not always be possible.

This is why Kedro provides a built-in [PartitionedDataset](/kedro_datasets.partitions.PartitionedDataset), with the following features:

* `PartitionedDataset` can recursively load/save all or specific files from a given location.
* It is platform agnostic, and can work with any filesystem implementation supported by [fsspec](https://filesystem-spec.readthedocs.io/) including local, S3, GCS, and many more.
* It implements a [lazy loading](https://en.wikipedia.org/wiki/Lazy_loading) approach, and does not attempt to load any partition data until a processing node explicitly requests it.
* It supports lazy saving by using `Callable`s.

```{note}
In this section, each individual file inside a given location is called a partition.
```

### How to use `PartitionedDataset`

You can use a `PartitionedDataset` in `catalog.yml` file like any other regular dataset definition:

```yaml
# conf/base/catalog.yml

my_partitioned_dataset:
  type: PartitionedDataset
  path: s3://my-bucket-name/path/to/folder  # path to the location of partitions
  dataset: pandas.CSVDataset  # shorthand notation for the dataset which will handle individual partitions
  credentials: my_credentials
  load_args:
    load_arg1: value1
    load_arg2: value2
```

```{note}
Like any other dataset, `PartitionedDataset` can also be instantiated programmatically in Python:
```

```python
from kedro_datasets.pandas import CSVDataset
from kedro.io import PartitionedDataset

my_credentials = {...}  # credentials dictionary

my_partitioned_dataset = PartitionedDataset(
    path="s3://my-bucket-name/path/to/folder",
    dataset=CSVDataset,
    credentials=my_credentials,
    load_args={"load_arg1": "value1", "load_arg2": "value2"},
)
```

Alternatively, if you need more granular configuration of the underlying dataset, its definition can be provided in full:

```yaml
# conf/base/catalog.yml

my_partitioned_dataset:
  type: PartitionedDataset
  path: s3://my-bucket-name/path/to/folder
  dataset:  # full dataset config notation
    type: pandas.CSVDataset
    load_args:
      delimiter: ","
    save_args:
      index: false
  credentials: my_credentials
  load_args:
    load_arg1: value1
    load_arg2: value2
  filepath_arg: filepath  # the argument of the dataset to pass the filepath to
  filename_suffix: ".csv"
```

Here is an exhaustive list of the arguments supported by `PartitionedDataset`:

| Argument          | Required                       | Supported types                                  | Description                                                                                                                                                                                                                                   |
| ----------------- | ------------------------------ | ------------------------------------------------ |-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `path`            | Yes                            | `str`                                            | Path to the folder containing partitioned data. If path starts with the protocol (e.g., `s3://`) then the corresponding `fsspec` concrete filesystem implementation will be used. If protocol is not specified, local filesystem will be used |
| `dataset`         | Yes                            | `str`, `Type[AbstractDataset]`, `Dict[str, Any]` | Underlying dataset definition, for more details see the section below                                                                                                                                                                         |
| `credentials`     | No                             | `Dict[str, Any]`                                 | Protocol-specific options that will be passed to `fsspec.filesystemcall`, for more details see the section below                                                                                                                              |
| `load_args`       | No                             | `Dict[str, Any]`                                 | Keyword arguments to be passed into `find()` method of the corresponding filesystem implementation                                                                                                                                            |
| `filepath_arg`    | No                             | `str` (defaults to `filepath`)                   | Argument name of the underlying dataset initialiser that will contain a path to an individual partition                                                                                                                                       |
| `filename_suffix` | No                             | `str` (defaults to an empty string)              | If specified, partitions that don't end with this string will be ignored                                                                                                                                                                      |

### Dataset definition

The dataset definition should be passed into the `dataset` argument of the `PartitionedDataset`. The dataset definition is used to instantiate a new dataset object for each individual partition, and use that dataset object for load and save operations. Dataset definition supports shorthand and full notations.

#### Shorthand notation

Requires you only to specify a class of the underlying dataset either as a string (e.g. `pandas.CSVDataset` or a fully qualified class path like `kedro_datasets.pandas.CSVDataset`) or as a class object that is a subclass of the [AbstractDataset](/kedro.io.AbstractDataset).

#### Full notation

Full notation allows you to specify a dictionary with the full underlying dataset definition _except_ the following arguments:
* The argument that receives the partition path (`filepath` by default) - if specified, a `UserWarning` will be emitted stating that this value will be overridden by individual partition paths
* `credentials` key - specifying it will result in a `DatasetError` being raised; dataset credentials should be passed into the `credentials` argument of the `PartitionedDataset` rather than the underlying dataset definition - see the section below on [partitioned dataset credentials](#partitioned-dataset-credentials) for details
* `versioned` flag - specifying it will result in a `DatasetError` being raised; versioning cannot be enabled for the underlying datasets

### Partitioned dataset credentials

```{note}
Support for `dataset_credentials` key in the credentials for `PartitionedDataset` is now deprecated. The dataset credentials should be specified explicitly inside the dataset config.
```

Credentials management for `PartitionedDataset` is somewhat special, because it might contain credentials for both `PartitionedDataset` itself _and_ the underlying dataset that is used for partition load and save. Top-level credentials are passed to the underlying dataset config (unless such config already has credentials configured), but not the other way around - dataset credentials are never propagated to the filesystem.

Here is the full list of possible scenarios:

| Top-level credentials | Underlying dataset credentials | Example `PartitionedDataset` definition                                                                                                                                    | Description                                                                                                                                                                                     |
| --------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Undefined             | Undefined                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset="pandas.CSVDataset")`                                                                                  | Credentials are not passed to the underlying dataset or the filesystem                                                                                                                          |
| Undefined             | Specified                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset={"type": "pandas.CSVDataset", "credentials": {"secret": True}})`                                       | Underlying dataset credentials are passed to the `CSVDataset` constructor, filesystem is instantiated without credentials                                                                       |
| Specified             | Undefined                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset="pandas.CSVDataset", credentials={"secret": True})`                                                    | Top-level credentials are passed to the underlying `CSVDataset` constructor and the filesystem                                                                                                  |
| Specified             | `None`                         | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset={"type": "pandas.CSVDataset", "credentials": None}, credentials={"dataset_secret": True})`             | Top-level credentials are passed to the filesystem, `CSVDataset` is instantiated without credentials - this way you can stop the top-level credentials from propagating into the dataset config |
| Specified             | Specified                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset={"type": "pandas.CSVDataset", "credentials": {"dataset_secret": True}}, credentials={"secret": True})` | Top-level credentials are passed to the filesystem, underlying dataset credentials are passed to the `CSVDataset` constructor                                                                   |

### Partitioned dataset load

Let's assume that the Kedro pipeline that you are working with contains the node, defined as follows:

```python
from kedro.pipeline import node

node(concat_partitions, inputs="my_partitioned_dataset", outputs="concatenated_result")
```

The underlying node function `concat_partitions` might look like this:

```python
from typing import Any, Callable, Dict
import pandas as pd


def concat_partitions(partitioned_input: Dict[str, Callable[[], Any]]) -> pd.DataFrame:
    """Concatenate input partitions into one pandas DataFrame.

    Args:
        partitioned_input: A dictionary with partition ids as keys and load functions as values.

    Returns:
        Pandas DataFrame representing a concatenation of all loaded partitions.
    """
    result = pd.DataFrame()

    for partition_key, partition_load_func in sorted(partitioned_input.items()):
        partition_data = partition_load_func()  # load the actual partition data
        # concat with existing result
        result = pd.concat([result, partition_data], ignore_index=True, sort=True)

    return result
```

As you can see from the above example, on load `PartitionedDataset` _does not_ automatically load the data from the located partitions. Instead, `PartitionedDataset` returns a dictionary with partition IDs as keys and the corresponding load functions as values. It allows the node that consumes the `PartitionedDataset` to implement the logic that defines what partitions need to be loaded, and how this data is going to be processed.

Partition ID _does not_ represent the whole partition path, but only a part of it that is unique for a given partition _and_ filename suffix:

* Example 1: if `path=s3://my-bucket-name/folder` and partition is stored in `s3://my-bucket-name/folder/2019-12-04/data.csv`, then its Partition ID is `2019-12-04/data.csv`.


* Example 2: if `path=s3://my-bucket-name/folder` and `filename_suffix=".csv"` and partition is stored in `s3://my-bucket-name/folder/2019-12-04/data.csv`, then its Partition ID is `2019-12-04/data`.

`PartitionedDataset` implements caching on load operation, which means that if multiple nodes consume the same `PartitionedDataset`, they will all receive the same partition dictionary even if some new partitions were added to the folder after the first load has been completed. This is done deliberately to guarantee the consistency of load operations between the nodes and avoid race conditions. To reset the cache, call the `release()` method of the partitioned dataset object.

### Partitioned dataset save

`PartitionedDataset` also supports a save operation. Let's assume the following configuration:

```yaml
# conf/base/catalog.yml

new_partitioned_dataset:
  type: PartitionedDataset
  path: s3://my-bucket-name
  dataset: pandas.CSVDataset
  filename_suffix: ".csv"
```

Here is the node definition:

```python
from kedro.pipeline import node

node(create_partitions, inputs=None, outputs="new_partitioned_dataset")
```

The underlying node function is as follows in `create_partitions`:

```python
from typing import Any, Dict
import pandas as pd


def create_partitions() -> Dict[str, Any]:
    """Create new partitions and save using PartitionedDataset.

    Returns:
        Dictionary with the partitions to create.
    """
    return {
        # create a file "s3://my-bucket-name/part/foo.csv"
        "part/foo": pd.DataFrame({"data": [1, 2]}),
        # create a file "s3://my-bucket-name/part/bar.csv.csv"
        "part/bar.csv": pd.DataFrame({"data": [3, 4]}),
    }
```

```{note}
Writing to an existing partition may result in its data being overwritten, if this case is not specifically handled by the underlying dataset implementation. You should implement your own checks to ensure that no existing data is lost when writing to a `PartitionedDataset`. The simplest safety mechanism could be to use partition IDs with a high chance of uniqueness: for example, the current timestamp.
```

### Partitioned dataset lazy saving
`PartitionedDataset` also supports lazy saving, where the partition's data is not materialised until it is time to write.

To use this, simply return `Callable` types in the dictionary:

```python
from typing import Any, Dict, Callable
import pandas as pd


def create_partitions() -> Dict[str, Callable[[], Any]]:
    """Create new partitions and save using PartitionedDataset.

    Returns:
        Dictionary of the partitions to create to a function that creates them.
    """
    return {
        # create a file "s3://my-bucket-name/part/foo.csv"
        "part/foo": lambda: pd.DataFrame({"data": [1, 2]}),
        # create a file "s3://my-bucket-name/part/bar.csv"
        "part/bar": lambda: pd.DataFrame({"data": [3, 4]}),
    }
```

```{note}
When using lazy saving, the dataset will be written _after_ the `after_node_run` [hook](../hooks/introduction).
```

## Incremental datasets

[IncrementalDataset](/kedro_datasets.partitions.IncrementalDataset) is a subclass of `PartitionedDataset`, which stores the information about the last processed partition in the so-called `checkpoint`. `IncrementalDataset` addresses the use case when partitions have to be processed incrementally, that is, each subsequent pipeline run should process just the partitions which were not processed by the previous runs.

This checkpoint, by default, is persisted to the location of the data partitions. For example, for `IncrementalDataset` instantiated with path `s3://my-bucket-name/path/to/folder`, the checkpoint will be saved to `s3://my-bucket-name/path/to/folder/CHECKPOINT`, unless [the checkpoint configuration is explicitly overwritten](#checkpoint-configuration).

The checkpoint file is only created _after_ [the partitioned dataset is explicitly confirmed](#incremental-dataset-confirm).

### Incremental dataset loads

Loading `IncrementalDataset` works similarly to [`PartitionedDataset`](#partitioned-dataset-load) with several exceptions:
1. `IncrementalDataset` loads the data _eagerly_, so the values in the returned dictionary represent the actual data stored in the corresponding partition, rather than a pointer to the load function. `IncrementalDataset` considers a partition relevant for processing if its ID satisfies the comparison function, given the checkpoint value.
2. `IncrementalDataset` _does not_ raise a `DatasetError` if load finds no partitions to return - an empty dictionary is returned instead. An empty list of available partitions is part of a normal workflow for `IncrementalDataset`.

### Incremental dataset save

The `IncrementalDataset` save operation is identical to the [save operation of the `PartitionedDataset`](#partitioned-dataset-save).

### Incremental dataset confirm

```{note}
The checkpoint value *is not* automatically updated when a new set of partitions is successfully loaded or saved.
```

Partitioned dataset checkpoint update is triggered by an explicit `confirms` instruction in one of the nodes downstream. It can be the same node, which processes the partitioned dataset:

```python
from kedro.pipeline import node

# process and then confirm `IncrementalDataset` within the same node
node(
    process_partitions,
    inputs="my_partitioned_dataset",
    outputs="my_processed_dataset",
    confirms="my_partitioned_dataset",
)
```

Alternatively, confirmation can be deferred to one of the nodes downstream, allowing you to implement extra validations before the loaded partitions are considered successfully processed:

```python
from kedro.pipeline import node, pipeline

pipeline(
    [
        node(
            func=process_partitions,
            inputs="my_partitioned_dataset",
            outputs="my_processed_dataset",
        ),
        # do something else
        node(
            func=confirm_partitions,
            # note that the node may not require 'my_partitioned_dataset' as an input
            inputs="my_processed_dataset",
            outputs=None,
            confirms="my_partitioned_dataset",
        ),
        # ...
        node(
            func=do_something_else_with_partitions,
            # will return the same partitions even though they were already confirmed
            inputs=["my_partitioned_dataset", "my_processed_dataset"],
            outputs=None,
        ),
    ]
)
```

Important notes about the confirmation operation:

* Confirming a partitioned dataset does not affect any subsequent loads within the same run. All downstream nodes that input the same partitioned dataset as input will all receive the _same_ partitions. Partitions that are created externally during the run will also not affect the dataset loads and won't appear in the list of loaded partitions until the next run or until the [`release()`](/kedro_datasets.partitions.IncrementalDataset) method is called on the dataset object.
* A pipeline cannot contain more than one node confirming the same dataset.


### Checkpoint configuration

`IncrementalDataset` does not require explicit configuration of the checkpoint unless there is a need to deviate from the defaults. To update the checkpoint configuration, add a `checkpoint` key containing the valid dataset configuration. This may be required if, say, the pipeline has read-only permissions to the location of partitions (or write operations are undesirable for any other reason). In such cases, `IncrementalDataset` can be configured to save the checkpoint elsewhere. The `checkpoint` key also supports partial config updates where only some checkpoint attributes are overwritten, while the defaults are kept for the rest:

```yaml
my_partitioned_dataset:
  type: IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint:
    # update the filepath and load_args, but keep the dataset type unchanged
    filepath: gcs://other-bucket/CHECKPOINT
    load_args:
      k1: v1
```

### Special checkpoint config keys

Along with the standard dataset attributes, `checkpoint` config also accepts two special optional keys:
* `comparison_func` (defaults to `operator.gt`) - a fully qualified import path to the function that will be used to compare a partition ID with the checkpoint value, to determine whether a partition should be processed. Such functions must accept two positional string arguments - partition ID and checkpoint value - and return `True` if such partition is considered to be past the checkpoint. It might be useful to specify your own `comparison_func` if you need to customise the checkpoint filtration mechanism - for example, you might want to implement windowed loading, where you always want to load the partitions representing the last calendar month. See the example config specifying a custom comparison function:

```yaml
my_partitioned_dataset:
  type: IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint:
    comparison_func: my_module.path.to.custom_comparison_function  # the path must be importable
```

* `force_checkpoint` - if set, the partitioned dataset will use this value as the checkpoint instead of loading the corresponding checkpoint file. This might be useful if you need to roll back the processing steps and reprocess some (or all) of the available partitions. See the example config forcing the checkpoint value:

```yaml
my_partitioned_dataset:
  type: IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint:
    force_checkpoint: 2020-01-01/data.csv
```

```{note}
Specification of `force_checkpoint` is also supported via the shorthand notation, as follows:
```

```yaml
my_partitioned_dataset:
  type: IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint: 2020-01-01/data.csv
```

```{note}
If you need to force the partitioned dataset to load all available partitions, set `checkpoint` to an empty string:
```

```yaml
my_partitioned_dataset:
  type: IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint: ""
```
