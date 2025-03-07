# Data versioning with Iceberg

[Apache Iceberg](https://iceberg.apache.org/) is an open table format for analytic datasets. Iceberg tables offer features such as schema evolution, hidden partitioning, partition layout evolution, time travel, and version rollback. This guide explains how to use Iceberg tables with Kedro. For this tutorial, we will use [`pyiceberg`](https://py.iceberg.apache.org/) which is a library that allows you to interact with Iceberg tables using Python, without the need of a JVM. It is important to note that `pyiceberg` is a fast evolving project and does not support the full range of features that Iceberg tables offer. You can use this tutorial as inspiration to extend the functionality using different compute engines such as [Spark](https://iceberg.apache.org/docs/nightly/spark-getting-started/), or dataframe technologies such as [Apache Arrow, DuckDB, and more](https://py.iceberg.apache.org/api/#query-the-data) by [creating your own custom datasets](../data/how_to_create_a_custom_dataset.md).

## Prerequisites

You will need to create a `spaceflights-pandas` starter project which contains example pipelines to work with called `kedro-iceberg`. If you haven't already, you can create a new Kedro project using the following command:

```bash
kedro new --starter spaceflights-pandas --name kedro-iceberg
```

To interact with Iceberg tables, you will also need the `pyiceberg` package installed. You can install it by adding the following line to your `requirements.txt`:

```bash
pyiceberg[pyarrow]~=0.8.0
```
Depending on your choice of storage, you may also need to install the optional dependencies. Consult [the installation guide for `PyIceberg`](https://py.iceberg.apache.org/#installation) to update the line above with the necessary optional dependencies.

Now you can install the project requirements with the following command:
```
pip install -r requirements.txt
```
### Set up the Iceberg catalog

Iceberg tables are managed by a catalog which is responsible for managing the metadata of the tables. In production, this could be a Hive, Glue, or [other catalog supported by Apache Iceberg](https://py.iceberg.apache.org/configuration/#catalogs). Iceberg also supports various storage options such as S3, HDFS, and more. There are multiple ways you can configure the catalog, credentials, and object storage to suit your needs by referring to the [configuration guide](https://py.iceberg.apache.org/configuration/). For this tutorial, we will use the `SQLCatalog` which stores the metadata in a local `sqlite` database and uses the local filesystem for storage.

Create a temporary location for Iceberg tables by running the following command:

```bash
mkdir -p /tmp/warehouse
```
There are multiple ways to configure the catalog, and for this tutorial, you can use the `~/.pyiceberg.yaml` file. By default, `pyiceberg` looks for the `.pyiceberg.yaml` file in your home directory, that is, it looks for `~/.pyiceberg.yaml`. You can create or update the existing file `.pyiceberg.yaml` in your home directory with the following content:

```yaml
catalog:
  default:
    type: sql
    uri: sqlite:////tmp/warehouse/pyiceberg_catalog.db
    warehouse: file:///tmp/warehouse/warehouse
```
You can check if the configuration is loading by opening a Python shell with `ipython` command and running the following code:

```python
from pyiceberg.catalog import load_catalog
catalog = load_catalog(name="default")
```
## Define a custom dataset to use Iceberg tables

To use the Iceberg tables with Kedro, you will need to define a [custom dataset that uses the `pyiceberg` library](../data/how_to_create_a_custom_dataset.md). Create a new file  called `pyiceberg_dataset.py` in the `src/kedro_iceberg/` directory of your project and copy the following code:

```python
import pyarrow as pa
from kedro.io.core import AbstractDataset, DatasetError
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError

DEFAULT_LOAD_ARGS = {"load_version": None}
DEFAULT_SAVE_ARGS = {"mode": "overwrite"}

class PyIcebergDataset(AbstractDataset):
    def __init__(
            self,
            catalog,
            namespace,
            table_name,
            load_args=DEFAULT_LOAD_ARGS,
            scan_args=None,
            save_args=DEFAULT_SAVE_ARGS,
    ):
        self.table_name = table_name
        self.namespace = namespace
        self.catalog = load_catalog(catalog)
        self.load_args = load_args
        self.table = self._load_table(namespace, table_name)
        self.save_args = save_args
        self.scan_args = scan_args


    def load(self):
        self.table = self.catalog.load_table((self.namespace, self.table_name))
        if self.scan_args:
            scan = self.table.scan(**self.scan_args)
        else:
            scan = self.table.scan()
        return scan.to_pandas()

    def _load_table(self, namespace, table_name):
        try:
            return self.catalog.load_table((namespace, table_name))
        except NoSuchTableError:
            return None

    def save(self, data) -> None:
        arrow = pa.Table.from_pandas(data)
        if not self.table:
            self.catalog.create_namespace_if_not_exists(self.namespace)
            self.table = self.catalog.create_table((self.namespace, self.table_name), schema=arrow.schema)
        if self.save_args.get("mode") == "overwrite":
            self.table.overwrite(arrow)
        elif self.save_args.get("mode") == "append":
            self.table.append(arrow)
        else:
            raise DatasetError("Mode not supported")

    def _describe(self) -> dict:
        return {}

    def exists(self):
        return self.catalog.table_exists((self.namespace, self.table_name))

    def inspect(self):
        return self.table.inspect
```

This dataset allows you to load Iceberg tables as `pandas` dataframes. You can also load a subset of the table by passing [the `scan_args` parameter to the dataset](https://py.iceberg.apache.org/reference/pyiceberg/table/#pyiceberg.table.Table.scan). The `save()` method allows you to save a dataframe as an Iceberg table. You can specify the mode of saving the table by passing the `save_args` parameter to the dataset. The `inspect()` method returns an `InspectTable` object which contains metadata about the table.
You can also update the code to extend the functionality of the dataset to support more features of Iceberg tables. Refer to the [Iceberg API documentation](https://py.iceberg.apache.org/api/) to see what you can do with the `Table` object.

## Using Iceberg tables in the catalog

### Save the dataset as an Iceberg table

Now update your catalog in `conf/base/catalog.yml` to update the `model_input_table` dataset to use the custom `PyIcebergDataset`:

```yaml
model_input_table:
  type: kedro_iceberg.pyiceberg_dataset.PyIcebergDataset
  catalog: default
  namespace: default
  table_name: model_input_table
```

Now run your Kedro project with the following command:

```bash
kedro run
```
You can inspect the `model_input_table` dataset created as an Iceberg table by running the following command:

```bash
tree /tmp/warehouse
```
The output should look something like:
```bash
/tmp/warehouse
├── pyiceberg_catalog.db
└── warehouse
    └── default.db
        └── model_input_table
            ├── data
            │   ├── 00000-0-a3d0f3e6-a9b4-44e4-8dac-95d4b5c14b29.parquet
            │   └── 00000-0-baa30a43-2cad-4507-967e-84c744d69c9b.parquet
            └── metadata
                ├── 00000-e66a465e-cdfa-458e-aaf3-aed48ac49157.metadata.json
                ├── 00001-d1fa7797-ef6f-438e-83c0-bdaabf1bd8de.metadata.json
                ├── 00002-f0b5294e-a0be-450c-95fe-4cee96c9a311.metadata.json
                ├── 836ecf2e-e339-44d8-933a-bd978991ea3e-m0.avro
                ├── a3d0f3e6-a9b4-44e4-8dac-95d4b5c14b29-m0.avro
                ├── baa30a43-2cad-4507-967e-84c744d69c9b-m0.avro
                ├── snap-3087457244520966174-0-836ecf2e-e339-44d8-933a-bd978991ea3e.avro
                ├── snap-3885749350984242152-0-a3d0f3e6-a9b4-44e4-8dac-95d4b5c14b29.avro
                └── snap-7387825159950300388-0-baa30a43-2cad-4507-967e-84c744d69c9b.avro
```

Suppose the upstream datasets `companies`, `shuttles`, or `reviews` are updated. You can run the following command to generate a new version of the `model_input_table` dataset:

```bash
kedro run --to-outputs=model_input_table
```
You can use the `find /tmp/warehouse/` command to inspect the updated dataset and logs.

### Load a specific dataset version

To load a specific version of the dataset, you can specify the `snapshot_id` of the version you want in the `scan_args` of the table in the configuration. You can get the `snapshot_id` from the history of the table. The section below explains how to inspect the history of the table in interactive mode.

```yaml
model_input_table:
  type: kedro_iceberg.pyiceberg_dataset.PyIcebergDataset
  catalog: default
  namespace: default
  table_name: model_input_table
  table_type: pandas
  scan_args:
    snapshot_id: <snapshot_id>
```

## Inspect the dataset in interactive mode

You can inspect the history, metadata, schema, and more of the Iceberg table in an interactive Python session. To start the IPython session with Kedro components loaded, run:

```bash
kedro ipython
```
Load the instance of the `PyIcebergDataset` using the `catalog.datasets` attribute:

```python
In [1]: model_input_table = catalog.datasets['model_input_table']
```
You can inspect the history of the Delta table by accessing the `InspectTable` object with the `inspect()` method:

```python
In [2]: inspect_table = model_input_table.inspect()
```
Now you can call the `history()` method on the `InspectTable` object to get the history of the table:

```python
In [3]: inspect_table.history()
Out [3]:

pyarrow.Table
made_current_at: timestamp[ms] not null
snapshot_id: int64 not null
parent_id: int64
is_current_ancestor: bool not null
----
made_current_at: [[2025-02-26 11:42:36.871,2025-02-26 12:08:38.826,2025-02-26 12:08:38.848]]
snapshot_id: [[9089827653240705573,5091346767047746426,7107920212859354452]]
parent_id: [[null,9089827653240705573,5091346767047746426]]
is_current_ancestor: [[true,true,true]]
```

Alternatively, you can also call the `history()` method from the `pyiceberg.table.Table` object directly which shows a more consise output:

```python
In [4]: model_input_table.table.history()
Out [4]:
[
    SnapshotLogEntry(snapshot_id=7387825159950300388, timestamp_ms=1741190825900),
    SnapshotLogEntry(snapshot_id=3087457244520966174, timestamp_ms=1741190833531),
    SnapshotLogEntry(snapshot_id=3885749350984242152, timestamp_ms=1741190833554)
]
```

Similarly, you can call [other methods on the `InspectTable` object](https://py.iceberg.apache.org/api/#inspecting-tables) to get more information about the table, such as `snapshots()`, `schema()`, `partitions()`, and more.
