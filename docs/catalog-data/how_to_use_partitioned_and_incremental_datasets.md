# How to use partitioned and incremental datasets

This guide shows how to configure and use `PartitionedDataset` and `IncrementalDataset`. For the concepts behind partition IDs, credentials, lazy saving, and checkpoints, see the [concept page](partitioned_and_incremental_datasets.md).

## How to define a `PartitionedDataset`

You can use a `PartitionedDataset` in `catalog.yml` like any other dataset definition:

```yaml
# conf/base/catalog.yml

my_partitioned_dataset:
  type: partitions.PartitionedDataset
  path: s3://my-bucket-name/path/to/folder  # path to the location of partitions
  dataset: pandas.CSVDataset  # shorthand notation for the dataset which will handle individual partitions
  credentials: my_credentials
  load_args:
    load_arg1: value1
    load_arg2: value2
```

!!! note
    Like any other dataset, `PartitionedDataset` can also be instantiated programmatically in Python.

```python
from kedro_datasets.pandas import CSVDataset
from kedro_datasets.partitions import PartitionedDataset

my_credentials = {...}  # credentials dictionary

my_partitioned_dataset = PartitionedDataset(
    path="s3://my-bucket-name/path/to/folder",
    dataset=CSVDataset,
    credentials=my_credentials,
    load_args={"load_arg1": "value1", "load_arg2": "value2"},
)
```

If you need more granular configuration of the underlying dataset, provide its definition in full:

```yaml
# conf/base/catalog.yml

my_partitioned_dataset:
  type: partitions.PartitionedDataset
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

For the full set of `PartitionedDataset` arguments and the rules around shorthand and full dataset notation, see the [concept page](partitioned_and_incremental_datasets.md#partitioneddataset-arguments).

## How partitioned dataset credentials interact

The table below covers every combination of top-level credentials on `PartitionedDataset` and credentials defined on the underlying dataset:

| Top-level credentials | Underlying dataset credentials | Example `PartitionedDataset` definition                                                                                                                                    | Description                                                                                                                                                                                     |
| --------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Undefined             | Undefined                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset="pandas.CSVDataset")`                                                                                  | Credentials are not passed to the underlying dataset or the filesystem.                                                                                                                          |
| Undefined             | Specified                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset={"type": "pandas.CSVDataset", "credentials": {"secret": True}})`                                       | Underlying dataset credentials are passed to the `CSVDataset` constructor; the filesystem is instantiated without credentials.                                                                       |
| Specified             | Undefined                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset="pandas.CSVDataset", credentials={"secret": True})`                                                    | Top-level credentials are passed to the underlying `CSVDataset` constructor and the filesystem.                                                                                                  |
| Specified             | `None`                         | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset={"type": "pandas.CSVDataset", "credentials": None}, credentials={"dataset_secret": True})`             | Top-level credentials are passed to the filesystem; `CSVDataset` is instantiated without credentials. This is how you stop the top-level credentials from propagating into the dataset config. |
| Specified             | Specified                      | `PartitionedDataset(path="s3://bucket-name/path/to/folder", dataset={"type": "pandas.CSVDataset", "credentials": {"dataset_secret": True}}, credentials={"secret": True})` | Top-level credentials are passed to the filesystem; underlying dataset credentials are passed to the `CSVDataset` constructor.                                                                   |

## How to load partitions in a node

Assume that the Kedro pipeline you are working with contains the following node:

```python
from kedro.pipeline import Node

Node(concat_partitions, inputs="my_partitioned_dataset", outputs="concatenated_result")
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

`PartitionedDataset` does not load partition data on its own — the node decides which partitions to load and how to process them. See [How partitions are identified](partitioned_and_incremental_datasets.md#how-partitions-are-identified) for the rules that determine partition IDs.

## How to save partitions from a node

`PartitionedDataset` also supports save operations. Assume the following configuration:

```yaml
# conf/base/catalog.yml

new_partitioned_dataset:
  type: partitions.PartitionedDataset
  path: s3://my-bucket-name
  dataset: pandas.CSVDataset
  filename_suffix: ".csv"
  save_lazily: True
```

And the following node definition:

```python
from kedro.pipeline import Node

Node(create_partitions, inputs=None, outputs="new_partitioned_dataset")
```

The underlying node function returns a dictionary keyed by partition IDs:

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

!!! note
    Writing to an existing partition may overwrite its data if the underlying dataset implementation does not handle this case. Add checks to ensure no existing data is lost. One safeguard is to use partition IDs with a high chance of uniqueness, such as the current timestamp.

## How to control lazy saving

To use lazy saving, return `Callable` types in the dictionary:

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

!!! note
    Lazy saving is enabled by default. When a `Callable` is provided, the dataset is written _after_ the `after_node_run` [hook](../extend/hooks/introduction.md) finishes.

To disable lazy saving, set `save_lazily: False`:

```yaml
# conf/base/catalog.yml

new_partitioned_dataset:
  type: partitions.PartitionedDataset
  path: s3://my-bucket-name
  dataset: pandas.CSVDataset
  filename_suffix: ".csv"
  save_lazily: False
```

!!! note
    If you create lambdas in a list/dictionary comprehension or a `for` loop, be careful when referencing variables defined outside the scope of the lambdas. See the [Python Programming FAQ](https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result) for an explanation of how this can result in unexpected values being returned from the lambdas.

## How to confirm incremental datasets

Partitioned dataset checkpoint update is triggered by an explicit `confirms` instruction on one of the downstream nodes. The simplest case is to confirm within the same node that processes the partitioned dataset:

```python
from kedro.pipeline import Node

# process and then confirm `IncrementalDataset` within the same node
Node(
    process_partitions,
    inputs="my_partitioned_dataset",
    outputs="my_processed_dataset",
    confirms="my_partitioned_dataset",
)
```

You can also defer confirmation to a downstream node to run additional validation before treating the loaded partitions as processed:

```python
from kedro.pipeline import Node, Pipeline

Pipeline(
    [
        Node(
            func=process_partitions,
            inputs="my_partitioned_dataset",
            outputs="my_processed_dataset",
        ),
        # do something else
        Node(
            func=confirm_partitions,
            # note that the node may not require 'my_partitioned_dataset' as an input
            inputs="my_processed_dataset",
            outputs=None,
            confirms="my_partitioned_dataset",
        ),
        # ...
        Node(
            func=do_something_else_with_partitions,
            # will return the same partitions even though they were already confirmed
            inputs=["my_partitioned_dataset", "my_processed_dataset"],
            outputs=None,
        ),
    ]
)
```

For the rules that govern when confirmation takes effect, see [the confirmation step](partitioned_and_incremental_datasets.md#the-confirmation-step).

## How to configure incremental dataset checkpoints

`IncrementalDataset` does not require explicit configuration of the checkpoint unless you need to deviate from the defaults. To override the checkpoint configuration, add a `checkpoint` key containing the valid dataset configuration. This is useful when the pipeline has read access to the location of partitions but no write permissions (or when write operations are undesirable). The `checkpoint` key also supports partial config updates, where a subset of checkpoint attributes is overwritten while the defaults are kept for the rest:

```yaml
my_partitioned_dataset:
  type: partitions.IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint:
    # update the filepath and load_args, but keep the dataset type unchanged
    filepath: gcs://other-bucket/CHECKPOINT
    load_args:
      k1: v1
```

To use a custom comparison function (for example, for windowed loading of the last calendar month):

```yaml
my_partitioned_dataset:
  type: partitions.IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint:
    comparison_func: my_module.path.to.custom_comparison_function  # the path must be importable
```

To force a specific checkpoint value (for example, to reprocess partitions from a known starting point):

```yaml
my_partitioned_dataset:
  type: partitions.IncrementalDataset
  path: s3://my-bucket-name/path/to/folder
  dataset: pandas.CSVDataset
  checkpoint:
    force_checkpoint: 2020-01-01/data.csv
```

!!! note
    Specifying `force_checkpoint` is also supported through shorthand notation:
    ```yaml
    my_partitioned_dataset:
      type: partitions.IncrementalDataset
      path: s3://my-bucket-name/path/to/folder
      dataset: pandas.CSVDataset
      checkpoint: 2020-01-01/data.csv
    ```

!!! note
    To force the partitioned dataset to load all available partitions, set `checkpoint` to an empty string:
    ```yaml
    my_partitioned_dataset:
      type: partitions.IncrementalDataset
      path: s3://my-bucket-name/path/to/folder
      dataset: pandas.CSVDataset
      checkpoint: ""
    ```
