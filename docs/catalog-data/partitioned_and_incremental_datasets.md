# Partitioned and incremental datasets

This page explains what `PartitionedDataset` and `IncrementalDataset` are, the model behind partition IDs, credentials, and checkpoints, and when each dataset type is the right choice. For step-by-step recipes covering YAML configuration, lazy saving, checkpoint customisation, and confirmation, see [how to use partitioned and incremental datasets](how_to_use_partitioned_and_incremental_datasets.md).

## Partitioned datasets

Distributed systems play an increasingly important role in ETL data pipelines. They increase processing throughput and let us work with much larger volumes of input data. A situation may arise where your Kedro node needs to read data from a directory full of uniform files of the same type, such as JSON or CSV. Tools like `PySpark` and the corresponding [SparkDataset](https://docs.kedro.org/projects/kedro-datasets/en/feature-8.0/api/kedro_datasets/spark.SparkDataset/) cater for such use cases but may not always be possible.

This is why Kedro provides [PartitionedDataset](https://docs.kedro.org/projects/kedro-datasets/en/feature-8.0/api/kedro_datasets/partitions.PartitionedDataset/) with the following features:

* `PartitionedDataset` can recursively load and save all or specific files from a given location.
* It is platform agnostic and can work with any filesystem implementation supported by [fsspec](https://filesystem-spec.readthedocs.io/), including local, S3, GCS, and others.
* It implements a [lazy loading](https://en.wikipedia.org/wiki/Lazy_loading) approach, and does not attempt to load any partition data until a processing node explicitly requests it.
* It supports lazy saving by using `Callable`s.

!!! note
    In this section, each individual file inside a given location is called a partition.

### `PartitionedDataset` arguments

Here is the full list of arguments supported by `PartitionedDataset`:

| Argument          | Required | Supported types                                  | Description                                                                                                                                                                                                                                   |
| ----------------- | -------- | ------------------------------------------------ |-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `path`            | Yes      | `str`                                            | Path to the folder containing partitioned data. If the path starts with a protocol (for example, `s3://`) the corresponding `fsspec` concrete filesystem implementation will be used. If no protocol is specified, the local filesystem will be used. |
| `dataset`         | Yes      | `str`, `Type[AbstractDataset]`, `Dict[str, Any]` | Underlying dataset definition. For details, see [Dataset definition](#dataset-definition).                                                                                                                                                    |
| `credentials`     | No       | `Dict[str, Any]`                                 | Protocol-specific options that will be passed to `fsspec.filesystem`. For details, see [Partitioned dataset credentials](#partitioned-dataset-credentials).                                                                                                              |
| `load_args`       | No       | `Dict[str, Any]`                                 | Keyword arguments to be passed into the `find()` method of the corresponding filesystem implementation.                                                                                                                                       |
| `filepath_arg`    | No       | `str` (defaults to `filepath`)                   | Argument name of the underlying dataset initialiser that will contain a path to an individual partition.                                                                                                                                       |
| `filename_suffix` | No       | `str` (defaults to an empty string)              | If specified, partitions that don't end with this string will be ignored.                                                                                                                                                                      |

### Dataset definition

The dataset definition is passed into the `dataset` argument of the `PartitionedDataset`. It is used to instantiate a new dataset object for each individual partition, and that dataset object is used for load and save operations. The definition supports a shorthand and a full notation.

**Shorthand notation**

Specify the underlying dataset class either as a string (for example, `pandas.CSVDataset` or a fully qualified class path like `kedro_datasets.pandas.CSVDataset`) or as a class object that is a subclass of [kedro.io.AbstractDataset][].

**Full notation**

The full notation allows you to specify a dictionary with the full underlying dataset definition _except_ the following arguments:

* The argument that receives the partition path (`filepath` by default) — if specified, a `UserWarning` is emitted stating that this value will be overridden by individual partition paths.
* `credentials` key — specifying it will result in a `DatasetError`. Dataset credentials should be passed into the `credentials` argument of the `PartitionedDataset` rather than the underlying dataset definition. See [Partitioned dataset credentials](#partitioned-dataset-credentials).
* `versioned` flag — specifying it will result in a `DatasetError`. Versioning cannot be enabled for the underlying datasets.

### Partitioned dataset credentials

!!! note
    Support for the `dataset_credentials` key in the credentials for `PartitionedDataset` is now deprecated. The dataset credentials should be specified explicitly inside the dataset config.

Credentials management for `PartitionedDataset` is somewhat special, because it may contain credentials for both `PartitionedDataset` itself _and_ the underlying dataset that is used for partition load and save. Top-level credentials are passed to the underlying dataset config (unless that config already has credentials configured), but not the other way around — dataset credentials are never propagated to the filesystem.

For a worked breakdown of every combination of top-level and underlying-dataset credentials, see [how partitioned dataset credentials interact](how_to_use_partitioned_and_incremental_datasets.md#how-partitioned-dataset-credentials-interact).

### How partitions are identified

On load, `PartitionedDataset` _does not_ automatically load the data from the located partitions. Instead, it returns a dictionary with partition IDs as keys and the corresponding load functions as values. This design lets the consuming node decide which partitions to load and how to process the data.

A partition ID _does not_ represent the whole partition path, but only the part of it that is unique to a given partition (and filename suffix):

* Example 1: if `path=s3://my-bucket-name/folder` and a partition is stored in `s3://my-bucket-name/folder/2019-12-04/data.csv`, its partition ID is `2019-12-04/data.csv`.
* Example 2: if `path=s3://my-bucket-name/folder` and `filename_suffix=".csv"` and a partition is stored in `s3://my-bucket-name/folder/2019-12-04/data.csv`, its partition ID is `2019-12-04/data`.

`PartitionedDataset` caches the load operation, which means that if multiple nodes consume the same `PartitionedDataset`, they all receive the same partition dictionary even if some new partitions were added to the folder after the first load completed. This behaviour guarantees consistent load operations between nodes and avoids race conditions. To reset the cache, call the `release()` method of the partitioned dataset object.

### Lazy saving

`PartitionedDataset` also supports lazy saving, where a partition's data is not materialised until it is time to write. Lazy saving is enabled by default: when a node returns a `Callable` value for a partition, the dataset is written _after_ the [`after_node_run` hook](../extend/hooks/introduction.md) finishes.

In certain cases, it might be useful to disable lazy saving — for example, when your object is already a `Callable` (such as a TensorFlow model) and you prefer to write the data straight away. See [how to control lazy saving](how_to_use_partitioned_and_incremental_datasets.md#how-to-control-lazy-saving) for the configuration.

## Incremental datasets

[IncrementalDataset](https://docs.kedro.org/projects/kedro-datasets/en/feature-8.0/api/kedro_datasets/partitions.IncrementalDataset/) is a subclass of `PartitionedDataset` that stores information about the last processed partition in a `checkpoint`. `IncrementalDataset` addresses the use case where partitions have to be processed incrementally — that is, each following pipeline run should process only the partitions that were not processed by previous runs.

This checkpoint, by default, is persisted to the location of the data partitions. For example, for an `IncrementalDataset` instantiated with path `s3://my-bucket-name/path/to/folder`, the checkpoint is saved to `s3://my-bucket-name/path/to/folder/CHECKPOINT`, unless the checkpoint configuration is explicitly overridden.

The checkpoint file is created _after_ the partitioned dataset is explicitly confirmed.

### How incremental loads differ from partitioned loads

Loading `IncrementalDataset` works similarly to `PartitionedDataset` with several exceptions:

1. `IncrementalDataset` loads data _eagerly_, so the values in the returned dictionary represent the actual data stored in the corresponding partition rather than a pointer to a load function. `IncrementalDataset` considers a partition relevant for processing if its ID satisfies the comparison function, given the checkpoint value.
2. `IncrementalDataset` _does not_ raise a `DatasetError` if load finds no partitions — an empty dictionary is returned instead. An empty list of available partitions is part of a normal workflow for `IncrementalDataset`.

The save operation is identical to that of `PartitionedDataset`.

### The confirmation step

The checkpoint value *is not* automatically updated when a new set of partitions is successfully loaded or saved. Checkpoint update is triggered by an explicit `confirms` instruction on one of the downstream nodes. This separation lets you defer confirmation until after additional validation has succeeded.

For worked examples covering same-node and deferred confirmation, see [how to confirm incremental datasets](how_to_use_partitioned_and_incremental_datasets.md#how-to-confirm-incremental-datasets).

Important notes about the confirmation operation:

* Confirming a partitioned dataset does not affect any following loads within the same run. All downstream nodes that take the same partitioned dataset as input will all receive the _same_ partitions. Partitions that are created externally during the run will not affect subsequent loads and won't appear in the list of loaded partitions until the next run, or until `release()` is called on the dataset object.
* A pipeline cannot contain more than one node confirming the same dataset.

### Checkpoint configuration

`IncrementalDataset` does not require explicit configuration of the checkpoint unless you need to deviate from the defaults. The `checkpoint` configuration accepts standard dataset attributes (used when the pipeline has read access to the location of partitions but no write access, for example) plus two special optional keys:

* `comparison_func` — a fully qualified import path to the function that compares a partition ID with the checkpoint value, used to determine whether a partition should be processed. Functions must accept two positional string arguments (partition ID and checkpoint value) and return `True` if the partition is considered to be past the checkpoint. The default is `operator.gt`. Customising `comparison_func` is useful when you need a different filtration mechanism (for example, windowed loading of the last calendar month).
* `force_checkpoint` — if set, the partitioned dataset uses this value as the checkpoint instead of loading the corresponding checkpoint file. This is useful when you need to roll back the processing steps and reprocess some (or all) of the available partitions.

For YAML examples of each, see [how to configure incremental dataset checkpoints](how_to_use_partitioned_and_incremental_datasets.md#how-to-configure-incremental-dataset-checkpoints).
