# Upcoming 0.17.0 release

## Major features and improvements

## Bug fixes and other changes

## Breaking changes to the API

## Thanks for supporting contributions

# Upcoming 0.16.6 release

## Major features and improvements

## Bug fixes and other changes
* Improved handling of non-ASCII word characters in dataset names.
  - For example, a dataset named `jalapeño` will be accessible as `DataCatalog.datasets.jalapeño` rather than `DataCatalog.datasets.jalape__o`.
* Fixed `kedro install` for an Anaconda environment defined in `environment.yml`.
* Fixed backwards compatibility with templates generated with older Kedro versions <0.16.5. No longer need to update `.kedro.yml` to use `kedro lint` and `kedro jupyter notebook convert`.
* Improved documentation.
* Added support for `compress_pickle` backend to `PickleDataSet`.

## Breaking changes to the API

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman), [Bhavya Merchant](https://github.com/bnmerchant), [Lovkush Agarwal](https://github.com/Lovkush-A), [Sasaki Takeru](https://github.com/takeru/)

# Release 0.16.5

## Major features and improvements
* Added the following new datasets.

| Type                        | Description                                                                                             | Location                      |
| --------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------- |
| `email.EmailMessageDataSet` | Manage email messages using [the Python standard library](https://docs.python.org/3/library/email.html) | `kedro.extras.datasets.email` |

* Added support for `pyproject.toml` to configure Kedro. `pyproject.toml` is used if `.kedro.yml` doesn't exist (Kedro configuration should be under `[tool.kedro]` section).
* Projects created with this version will have no `pipeline.py`, having been replaced by `hooks.py`.
* Added a set of registration hooks, as the new way of registering library components with a Kedro project:
    * `register_pipelines()`, to replace `_get_pipelines()`
    * `register_config_loader()`, to replace `_create_config_loader()`
    * `register_catalog()`, to replace `_create_catalog()`
These can be defined in `src/<package-name>/hooks.py` and added to `.kedro.yml` (or `pyproject.toml`). The order of execution is: plugin hooks, `.kedro.yml` hooks, hooks in `ProjectContext.hooks`.
* Added ability to disable auto-registered Hooks using `.kedro.yml` (or `pyproject.toml`) configuration file.

## Bug fixes and other changes
* Added option to run asynchronously via the Kedro CLI.
* Absorbed `.isort.cfg` settings into `setup.cfg`.
* Packaging a modular pipeline raises an error if the pipeline directory is empty or non-existent.

## Breaking changes to the API
* `project_name`, `project_version` and `package_name` now have to be defined in `.kedro.yml` for projects using Kedro 0.16.5+.

## Migration Guide
This release has accidentally broken the usage of `kedro lint` and `kedro jupyter notebook convert` on a project template generated with previous versions of Kedro (<=0.16.4). To amend this, please either upgrade to `kedro==0.16.6` or update `.kedro.yml` within your project root directory to include the following keys:

```yaml
project_name: "<your_project_name>"
project_version: "kedro_version_of_the_project>"
package_name: "<your_package_name>"
```

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman), [Bas Nijholt](https://github.com/basnijholt), [Sebastian Bertoli](https://github.com/sebastianbertoli)

# Release 0.16.4

## Major features and improvements
* Fixed a bug for using `ParallelRunner` on Windows.
* Enabled auto-discovery of hooks implementations coming from installed plugins.

## Bug fixes and other changes
* Fixed a bug for using `ParallelRunner` on Windows.
* Modified `GBQTableDataSet` to load customized results using customized queries from Google Big Query tables.
* Documentation improvements.

## Breaking changes to the API

## Thanks for supporting contributions
[Ajay Bisht](https://github.com/ajb7), [Vijay Sajjanar](https://github.com/vjkr), [Deepyaman Datta](https://github.com/deepyaman), [Sebastian Bertoli](https://github.com/sebastianbertoli), [Shahil Mawjee](https://github.com/s-mawjee), [Louis Guitton](https://github.com/louisguitton), [Emanuel Ferm](https://github.com/eferm)

# Release 0.16.3

## Major features and improvements
* Added the `kedro pipeline pull` CLI command to extract a packaged modular pipeline, and place the contents in a Kedro project.
* Added the `--version` option to `kedro pipeline package` to allow specifying alternative versions to package under.
* Added the `--starter` option to `kedro new` to create a new project from a local, remote or aliased starter template.
* Added the `kedro starter list` CLI command to list all starter templates that can be used to bootstrap a new Kedro project.
* Added the following new datasets.

| Type               | Description                                                                                           | Location                     |
| ------------------ | ----------------------------------------------------------------------------------------------------- | ---------------------------- |
| `json.JSONDataSet` | Work with JSON files using [the Python standard library](https://docs.python.org/3/library/json.html) | `kedro.extras.datasets.json` |

## Bug fixes and other changes
* Removed `/src/nodes` directory from the project template and made `kedro jupyter convert` create it on the fly if necessary.
* Fixed a bug in `MatplotlibWriter` which prevented saving lists and dictionaries of plots locally on Windows.
* Closed all pyplot windows after saving in `MatplotlibWriter`.
* Documentation improvements:
  - Added [kedro-wings](https://github.com/tamsanh/kedro-wings) and [kedro-great](https://github.com/tamsanh/kedro-great) to the list of community plugins.
* Fixed broken versioning for Windows paths.
* Fixed `DataSet` string representation for falsy values.
* Improved the error message when duplicate nodes are passed to the `Pipeline` initializer.
* Fixed a bug where `kedro docs` would fail because the built docs were located in a different directory.
* Fixed a bug where `ParallelRunner` would fail on Windows machines whose reported CPU count exceeded 61.
* Fixed an issue with saving TensorFlow model to `h5` file on Windows.
* Added a `json` parameter to `APIDataSet` for the convenience of generating requests with JSON bodies.
* Fixed dependencies for `SparkDataSet` to include spark.

## Breaking changes to the API

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman), [Tam-Sanh Nguyen](https://github.com/tamsanh), [DataEngineerOne](http://youtube.com/DataEngineerOne)

# Release 0.16.2

## Major features and improvements
* Added the following new datasets.

| Type                                | Description                                                                                                          | Location                           |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| `pandas.AppendableExcelDataSet`     | Work with `Excel` files opened in append mode                                                                        | `kedro.extras.datasets.pandas`     |
| `tensorflow.TensorFlowModelDataset` | Work with `TensorFlow` models using [TensorFlow 2.X](https://www.tensorflow.org/api_docs/python/tf/keras/Model#save) | `kedro.extras.datasets.tensorflow` |
| `holoviews.HoloviewsWriter`         | Work with `Holoviews` objects (saves as image file)                                                                  | `kedro.extras.datasets.holoviews`  |

* `kedro install` will now compile project dependencies (by running `kedro build-reqs` behind the scenes) before the installation if the `src/requirements.in` file doesn't exist.
* Added `only_nodes_with_namespace` in `Pipeline` class to filter only nodes with a specified namespace.
* Added the `kedro pipeline delete` command to help delete unwanted or unused pipelines (it won't remove references to the pipeline in your `create_pipelines()` code).
* Added the `kedro pipeline package` command to help package up a modular pipeline. It will bundle up the pipeline source code, tests, and parameters configuration into a .whl file.

## Bug fixes and other changes
* Improvement in `DataCatalog`:
  - Introduced regex filtering to the `DataCatalog.list()` method.
  - Non-alphanumeric characters (except underscore) in dataset name are replaced with `__` in `DataCatalog.datasets`, for ease of access to transcoded datasets.
* Improvement in Datasets:
  - Improved initialization speed of `spark.SparkHiveDataSet`.
  - Improved S3 cache in `spark.SparkDataSet`.
  - Added support of options for building `pyarrow` table in `pandas.ParquetDataSet`.
* Improvement in `kedro build-reqs` CLI command:
  - `kedro build-reqs` is now called with `-q` option and will no longer print out compiled requirements to the console for security reasons.
  - All unrecognized CLI options in `kedro build-reqs` command are now passed to [pip-compile](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) call (e.g. `kedro build-reqs --generate-hashes`).
* Improvement in `kedro jupyter` CLI command:
  - Improved error message when running `kedro jupyter notebook`, `kedro jupyter lab` or `kedro ipython` with Jupyter/IPython dependencies not being installed.
  - Fixed `%run_viz` line magic for showing kedro viz inside a Jupyter notebook. For the fix to be applied on existing Kedro project, please see the migration guide.
  - Fixed the bug in IPython startup script ([issue 298](https://github.com/quantumblacklabs/kedro/issues/298)).
* Documentation improvements:
  - Updated community-generated content in FAQ.
  - Added [find-kedro](https://github.com/WaylonWalker/find-kedro) and [kedro-static-viz](https://github.com/WaylonWalker/kedro-static-viz) to the list of community plugins.
  - Add missing `pillow.ImageDataSet` entry to the documentation.

## Breaking changes to the API

### Migration guide from Kedro 0.16.1 to 0.16.2

#### Guide to apply the fix for `%run_viz` line magic in existing project

Even though this release ships a fix for project generated with `kedro==0.16.2`, after upgrading, you will still need to make a change in your existing project if it was generated with `kedro>=0.16.0,<=0.16.1` for the fix to take effect. Specifically, please change the content of your project's IPython init script located at `.ipython/profile_default/startup/00-kedro-init.py` with the content of [this file](https://github.com/quantumblacklabs/kedro/blob/0.16.2/kedro/templates/project/%7B%7B%20cookiecutter.repo_name%20%7D%7D/.ipython/profile_default/startup/00-kedro-init.py). You will also need `kedro-viz>=3.3.1`.

## Thanks for supporting contributions
[Miguel Rodriguez Gutierrez](https://github.com/MigQ2), [Joel Schwarzmann](https://github.com/datajoely), [w0rdsm1th](https://github.com/w0rdsm1th), [Deepyaman Datta](https://github.com/deepyaman), [Tam-Sanh Nguyen](https://github.com/tamsanh), [Marcus Gawronsky](https://github.com/marcusinthesky)

# 0.16.1

## Major features and improvements

## Bug fixes and other changes
* Fixed deprecation warnings from `kedro.cli` and `kedro.context` when running `kedro jupyter notebook`.
* Fixed a bug where `catalog` and `context` were not available in Jupyter Lab and Notebook.
* Fixed a bug where `kedro build-reqs` would fail if you didn't have your project dependencies installed.

## Breaking changes to the API

## Thanks for supporting contributions

# 0.16.0

## Major features and improvements
### CLI
* Added new CLI commands (only available for the projects created using Kedro 0.16.0 or later):
  - `kedro catalog list` to list datasets in your catalog
  - `kedro pipeline list` to list pipelines
  - `kedro pipeline describe` to describe a specific pipeline
  - `kedro pipeline create` to create a modular pipeline
* Improved the CLI speed by up to 50%.
* Improved error handling when making a typo on the CLI. We now suggest some of the possible commands you meant to type, in `git`-style.

### Framework
* All modules in `kedro.cli` and `kedro.context` have been moved into `kedro.framework.cli` and `kedro.framework.context` respectively. `kedro.cli` and `kedro.context` will be removed in future releases.
* Added `Hooks`, which is a new mechanism for extending Kedro.
* Fixed `load_context` changing user's current working directory.
* Allowed the source directory to be configurable in `.kedro.yml`.
* Added the ability to specify nested parameter values inside your node inputs, e.g. `node(func, "params:a.b", None)`
### DataSets
* Added the following new datasets.

| Type                       | Description                                 | Location                          |
| -------------------------- | ------------------------------------------- | --------------------------------- |
| `pillow.ImageDataSet`      | Work with image files using `Pillow`        | `kedro.extras.datasets.pillow`    |
| `geopandas.GeoJSONDataSet` | Work with geospatial data using `GeoPandas` | `kedro.extras.datasets.geopandas` |
| `api.APIDataSet`           | Work with data from HTTP(S) API requests    | `kedro.extras.datasets.api`       |

* Added `joblib` backend support to `pickle.PickleDataSet`.
* Added versioning support to `MatplotlibWriter` dataset.
* Added the ability to install dependencies for a given dataset with more granularity, e.g. `pip install "kedro[pandas.ParquetDataSet]"`.
* Added the ability to specify extra arguments, e.g. `encoding` or `compression`, for `fsspec.spec.AbstractFileSystem.open()` calls when loading/saving a dataset. See Example 3 under [docs](https://kedro.readthedocs.io/en/stable/04_user_guide/04_data_catalog.html#using-the-data-catalog-with-the-yaml-api).

### Other
* Added `namespace` property on ``Node``, related to the modular pipeline where the node belongs.
* Added an option to enable asynchronous loading inputs and saving outputs in both `SequentialRunner(is_async=True)` and `ParallelRunner(is_async=True)` class.
* Added `MemoryProfiler` transformer.
* Removed the requirement to have all dependencies for a dataset module to use only a subset of the datasets within.
* Added support for `pandas>=1.0`.
* Enabled Python 3.8 compatibility. _Please note that a Spark workflow may be unreliable for this Python version as `pyspark` is not fully-compatible with 3.8 yet._
* Renamed "features" layer to "feature" layer to be consistent with (most) other layers and the [relevant FAQ](https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html#what-is-data-engineering-convention).

## Bug fixes and other changes
* Fixed a bug where a new version created mid-run by an external system caused inconsistencies in the load versions used in the current run.
* Documentation improvements
  * Added instruction in the documentation on how to create a custom runner).
  * Updated contribution process in `CONTRIBUTING.md` - added Developer Workflow.
  * Documented installation of development version of Kedro in the [FAQ section](https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html#how-can-i-use-a-development-version-of-kedro).
  * Added missing `_exists` method to `MyOwnDataSet` example in 04_user_guide/08_advanced_io.
* Fixed a bug where `PartitionedDataSet` and `IncrementalDataSet` were not working with `s3a` or `s3n` protocol.
* Added ability to read partitioned parquet file from a directory in `pandas.ParquetDataSet`.
* Replaced `functools.lru_cache` with `cachetools.cachedmethod` in `PartitionedDataSet` and `IncrementalDataSet` for per-instance cache invalidation.
* Implemented custom glob function for `SparkDataSet` when running on Databricks.
* Fixed a bug in `SparkDataSet` not allowing for loading data from DBFS in a Windows machine using Databricks-connect.
* Improved the error message for `DataSetNotFoundError` to suggest possible dataset names user meant to type.
* Added the option for contributors to run Kedro tests locally without Spark installation with `make test-no-spark`.
* Added option to lint the project without applying the formatting changes (`kedro lint --check-only`).

## Breaking changes to the API
### Datasets
* Deleted obsolete datasets from `kedro.io`.
* Deleted `kedro.contrib` and `extras` folders.
* Deleted obsolete `CSVBlobDataSet` and `JSONBlobDataSet` dataset types.
* Made `invalidate_cache` method on datasets private.
* `get_last_load_version` and `get_last_save_version` methods are no longer available on `AbstractDataSet`.
* `get_last_load_version` and `get_last_save_version` have been renamed to `resolve_load_version` and `resolve_save_version` on ``AbstractVersionedDataSet``, the results of which are cached.
* The `release()` method on datasets extending ``AbstractVersionedDataSet`` clears the cached load and save version. All custom datasets must call `super()._release()` inside `_release()`.
* ``TextDataSet`` no longer has `load_args` and `save_args`. These can instead be specified under `open_args_load` or `open_args_save` in `fs_args`.
* `PartitionedDataSet` and `IncrementalDataSet` method `invalidate_cache` was made private: `_invalidate_caches`.

### Other
* Removed `KEDRO_ENV_VAR` from `kedro.context` to speed up the CLI run time.
* `Pipeline.name` has been removed in favour of `Pipeline.tag()`.
* Dropped `Pipeline.transform()` in favour of `kedro.pipeline.modular_pipeline.pipeline()` helper function.
* Made constant `PARAMETER_KEYWORDS` private, and moved it from `kedro.pipeline.pipeline` to `kedro.pipeline.modular_pipeline`.
* Layers are no longer part of the dataset object, as they've moved to the `DataCatalog`.
* Python 3.5 is no longer supported by the current and all future versions of Kedro.

### Migration guide from Kedro 0.15.* to 0.16.*

#### General Migration

**reminder** [How do I upgrade Kedro](https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html#how-do-i-upgrade-kedro) covers a few key things to remember when updating any kedro version.

#### Migration for datasets

Since all the datasets (from `kedro.io` and `kedro.contrib.io`) were moved to `kedro/extras/datasets` you must update the type of all datasets in `<project>/conf/base/catalog.yml` file.
Here how it should be changed: `type: <SomeDataSet>` -> `type: <subfolder of kedro/extras/datasets>.<SomeDataSet>` (e.g. `type: CSVDataSet` -> `type: pandas.CSVDataSet`).

In addition, all the specific datasets like `CSVLocalDataSet`, `CSVS3DataSet` etc. were deprecated. Instead, you must use generalized datasets like `CSVDataSet`.
E.g. `type: CSVS3DataSet` -> `type: pandas.CSVDataSet`.

> Note: No changes required if you are using your custom dataset.

#### Migration for Pipeline.transform()
`Pipeline.transform()` has been dropped in favour of the `pipeline()` constructor. The following changes apply:
- Remember to import `from kedro.pipeline import pipeline`
- The `prefix` argument has been renamed to `namespace`
- And `datasets` has been broken down into more granular arguments:
  - `inputs`: Independent inputs to the pipeline
  - `outputs`: Any output created in the pipeline, whether an intermediary dataset or a leaf output
  - `parameters`: `params:...` or `parameters`

As an example, code that used to look like this with the `Pipeline.transform()` constructor:
```python
result = my_pipeline.transform(
    datasets={"input": "new_input", "output": "new_output", "params:x": "params:y"},
    prefix="pre"
)
```

When used with the new `pipeline()` constructor, becomes:
```python
from kedro.pipeline import pipeline

result = pipeline(
    my_pipeline,
    inputs={"input": "new_input"},
    outputs={"output": "new_output"},
    parameters={"params:x": "params:y"},
    namespace="pre"
)
```

#### Migration for decorators, color logger, transformers etc.
Since some modules were moved to other locations you need to update import paths appropriately.
You can find the list of moved files in the [`0.15.6` release notes](https://github.com/quantumblacklabs/kedro/releases/tag/0.15.6) under the section titled `Files with a new location`.

#### Migration for CLI and KEDRO_ENV environment variable
> Note: If you haven't made significant changes to your `kedro_cli.py`, it may be easier to simply copy the updated `kedro_cli.py` `.ipython/profile_default/startup/00-kedro-init.py` and from GitHub or a newly generated project into your old project.

* We've removed `KEDRO_ENV_VAR` from `kedro.context`. To get your existing project template working, you'll need to remove all instances of `KEDRO_ENV_VAR` from your project template:
  - From the imports in `kedro_cli.py` and `.ipython/profile_default/startup/00-kedro-init.py`: `from kedro.context import KEDRO_ENV_VAR, load_context` -> `from kedro.framework.context import load_context`
  - Remove the `envvar=KEDRO_ENV_VAR` line from the click options in `run`, `jupyter_notebook` and `jupyter_lab` in `kedro_cli.py`
  - Replace `KEDRO_ENV_VAR` with `"KEDRO_ENV"` in `_build_jupyter_env`
  - Replace `context = load_context(path, env=os.getenv(KEDRO_ENV_VAR))` with `context = load_context(path)` in `.ipython/profile_default/startup/00-kedro-init.py`

 #### Migration for `kedro build-reqs`

 We have upgraded `pip-tools` which is used by `kedro build-reqs` to 5.x. This `pip-tools` version requires `pip>=20.0`. To upgrade `pip`, please refer to [their documentation](https://pip.pypa.io/en/stable/installing/#upgrading-pip).

## Thanks for supporting contributions
[@foolsgold](https://github.com/foolsgold), [Mani Sarkar](https://github.com/neomatrix369), [Priyanka Shanbhag](https://github.com/priyanka1414), [Luis Blanche](https://github.com/LuisBlanche), [Deepyaman Datta](https://github.com/deepyaman), [Antony Milne](https://github.com/AntonyMilneQB), [Panos Psimatikas](https://github.com/ppsimatikas), [Tam-Sanh Nguyen](https://github.com/tamsanh), [Tomasz Kaczmarczyk](https://github.com/TomaszKaczmarczyk), [Kody Fischer](https://github.com/Klio-Foxtrot187), [Waylon Walker](https://github.com/waylonwalker)

# 0.15.9

## Major features and improvements

## Bug fixes and other changes

* Pinned `fsspec>=0.5.1, <0.7.0` and `s3fs>=0.3.0, <0.4.1` to fix incompatibility issues with their latest release.

## Breaking changes to the API

## Thanks for supporting contributions

# 0.15.8

## Major features and improvements

## Bug fixes and other changes

* Added the additional libraries to our `requirements.txt` so `pandas.CSVDataSet` class works out of box with `pip install kedro`.
* Added `pandas` to our `extra_requires` in `setup.py`.
* Improved the error message when dependencies of a `DataSet` class are missing.

## Breaking changes to the API

## Thanks for supporting contributions

# 0.15.7

## Major features and improvements

* Added in documentation on how to contribute a custom `AbstractDataSet` implementation.

## Bug fixes and other changes

* Fixed the link to the Kedro banner image in the documentation.

## Breaking changes to the API

## Thanks for supporting contributions

# 0.15.6

## Major features and improvements
> _TL;DR_ We're launching [`kedro.extras`](https://github.com/quantumblacklabs/kedro/tree/master/extras), the new home for our revamped series of datasets, decorators and dataset transformers. The datasets in [`kedro.extras.datasets`](https://github.com/quantumblacklabs/kedro/tree/master/extras/datasets) use [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to access a variety of data stores including local file systems, network file systems, cloud object stores (including S3 and GCP), and Hadoop, read more about this [**here**](https://kedro.readthedocs.io/en/latest/04_user_guide/04_data_catalog.html#specifying-the-location-of-the-dataset). The change will allow [#178](https://github.com/quantumblacklabs/kedro/issues/178) to happen in the next major release of Kedro.

An example of this new system can be seen below, loading the CSV `SparkDataSet` from S3:

```yaml
weather:
  type: spark.SparkDataSet  # Observe the specified type, this  affects all datasets
  filepath: s3a://your_bucket/data/01_raw/weather*  # filepath uses fsspec to indicate the file storage system
  credentials: dev_s3
  file_format: csv
```

You can also load data incrementally whenever it is dumped into a directory with the extension to [`PartionedDataSet`](https://kedro.readthedocs.io/en/latest/04_user_guide/08_advanced_io.html#partitioned-dataset), a feature that allows you to load a directory of files. The [`IncrementalDataSet`](https://kedro.readthedocs.io/en/stable/04_user_guide/08_advanced_io.html#incremental-loads-with-incrementaldataset) stores the information about the last processed partition in a `checkpoint`, read more about this feature [**here**](https://kedro.readthedocs.io/en/stable/04_user_guide/08_advanced_io.html#incremental-loads-with-incrementaldataset).

### New features

* Added `layer` attribute for datasets in `kedro.extras.datasets` to specify the name of a layer according to [data engineering convention](https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html#what-is-data-engineering-convention), this feature will be passed to [`kedro-viz`](https://github.com/quantumblacklabs/kedro-viz) in future releases.
* Enabled loading a particular version of a dataset in Jupyter Notebooks and iPython, using `catalog.load("dataset_name", version="<2019-12-13T15.08.09.255Z>")`.
* Added property `run_id` on `ProjectContext`, used for versioning using the [`Journal`](https://kedro.readthedocs.io/en/stable/04_user_guide/13_journal.html). To customise your journal `run_id` you can override the private method `_get_run_id()`.
* Added the ability to install all optional kedro dependencies via `pip install "kedro[all]"`.
* Modified the `DataCatalog`'s load order for datasets, loading order is the following:
  - `kedro.io`
  - `kedro.extras.datasets`
  - Import path, specified in `type`
* Added an optional `copy_mode` flag to `CachedDataSet` and `MemoryDataSet` to specify (`deepcopy`, `copy` or `assign`) the copy mode to use when loading and saving.

### New Datasets

| Type                             | Description                                                                                                                                      | Location                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| `dask.ParquetDataSet`            | Handles parquet datasets using Dask                                                                                                              | `kedro.extras.datasets.dask`        |
| `pickle.PickleDataSet`           | Work with Pickle files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem         | `kedro.extras.datasets.pickle`      |
| `pandas.CSVDataSet`              | Work with CSV files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem            | `kedro.extras.datasets.pandas`      |
| `pandas.TextDataSet`             | Work with text files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem           | `kedro.extras.datasets.pandas`      |
| `pandas.ExcelDataSet`            | Work with Excel files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem          | `kedro.extras.datasets.pandas`      |
| `pandas.HDFDataSet`              | Work with HDF using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem                  | `kedro.extras.datasets.pandas`      |
| `yaml.YAMLDataSet`               | Work with YAML files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem           | `kedro.extras.datasets.yaml`        |
| `matplotlib.MatplotlibWriter`    | Save with Matplotlib images using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem    | `kedro.extras.datasets.matplotlib`  |
| `networkx.NetworkXDataSet`       | Work with NetworkX files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem       | `kedro.extras.datasets.networkx`    |
| `biosequence.BioSequenceDataSet` | Work with bio-sequence objects using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem | `kedro.extras.datasets.biosequence` |
| `pandas.GBQTableDataSet`         | Work with Google BigQuery                                                                                                                        | `kedro.extras.datasets.pandas`      |
| `pandas.FeatherDataSet`          | Work with feather files using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem        | `kedro.extras.datasets.pandas`      |
| `IncrementalDataSet`             | Inherit from `PartitionedDataSet` and remembers the last processed partition                                                                     | `kedro.io`                          |

### Files with a new location

| Type                                                                 | New Location                                 |
| -------------------------------------------------------------------- | -------------------------------------------- |
| `JSONDataSet`                                                        | `kedro.extras.datasets.pandas`               |
| `CSVBlobDataSet`                                                     | `kedro.extras.datasets.pandas`               |
| `JSONBlobDataSet`                                                    | `kedro.extras.datasets.pandas`               |
| `SQLTableDataSet`                                                    | `kedro.extras.datasets.pandas`               |
| `SQLQueryDataSet`                                                    | `kedro.extras.datasets.pandas`               |
| `SparkDataSet`                                                       | `kedro.extras.datasets.spark`                |
| `SparkHiveDataSet`                                                   | `kedro.extras.datasets.spark`                |
| `SparkJDBCDataSet`                                                   | `kedro.extras.datasets.spark`                |
| `kedro/contrib/decorators/retry.py`                                  | `kedro/extras/decorators/retry_node.py`      |
| `kedro/contrib/decorators/memory_profiler.py`                        | `kedro/extras/decorators/memory_profiler.py` |
| `kedro/contrib/io/transformers/transformers.py`                      | `kedro/extras/transformers/time_profiler.py` |
| `kedro/contrib/colors/logging/color_logger.py`                       | `kedro/extras/logging/color_logger.py`       |
| `extras/ipython_loader.py`                                           | `tools/ipython/ipython_loader.py`            |
| `kedro/contrib/io/cached/cached_dataset.py`                          | `kedro/io/cached_dataset.py`                 |
| `kedro/contrib/io/catalog_with_default/data_catalog_with_default.py` | `kedro/io/data_catalog_with_default.py`      |
| `kedro/contrib/config/templated_config.py`                           | `kedro/config/templated_config.py`           |

## Upcoming deprecations

| Category                  | Type                                                           |
| ------------------------- | -------------------------------------------------------------- |
| **Datasets**              | `BioSequenceLocalDataSet`                                      |
|                           | `CSVGCSDataSet`                                                |
|                           | `CSVHTTPDataSet`                                               |
|                           | `CSVLocalDataSet`                                              |
|                           | `CSVS3DataSet`                                                 |
|                           | `ExcelLocalDataSet`                                            |
|                           | `FeatherLocalDataSet`                                          |
|                           | `JSONGCSDataSet`                                               |
|                           | `JSONLocalDataSet`                                             |
|                           | `HDFLocalDataSet`                                              |
|                           | `HDFS3DataSet`                                                 |
|                           | `kedro.contrib.io.cached.CachedDataSet`                        |
|                           | `kedro.contrib.io.catalog_with_default.DataCatalogWithDefault` |
|                           | `MatplotlibLocalWriter`                                        |
|                           | `MatplotlibS3Writer`                                           |
|                           | `NetworkXLocalDataSet`                                         |
|                           | `ParquetGCSDataSet`                                            |
|                           | `ParquetLocalDataSet`                                          |
|                           | `ParquetS3DataSet`                                             |
|                           | `PickleLocalDataSet`                                           |
|                           | `PickleS3DataSet`                                              |
|                           | `TextLocalDataSet`                                             |
|                           | `YAMLLocalDataSet`                                             |
| **Decorators**            | `kedro.contrib.decorators.memory_profiler`                     |
|                           | `kedro.contrib.decorators.retry`                               |
|                           | `kedro.contrib.decorators.pyspark.spark_to_pandas`             |
|                           | `kedro.contrib.decorators.pyspark.pandas_to_spark`             |
| **Transformers**          | `kedro.contrib.io.transformers.transformers`                   |
| **Configuration Loaders** | `kedro.contrib.config.TemplatedConfigLoader`                   |

## Bug fixes and other changes
* Added the option to set/overwrite params in `config.yaml` using YAML dict style instead of string CLI formatting only.
* Kedro CLI arguments `--node` and `--tag` support comma-separated values, alternative methods will be deprecated in future releases.
* Fixed a bug in the `invalidate_cache` method of `ParquetGCSDataSet` and `CSVGCSDataSet`.
* `--load-version` now won't break if version value contains a colon.
* Enabled running `node`s with duplicate inputs.
* Improved error message when empty credentials are passed into `SparkJDBCDataSet`.
* Fixed bug that caused an empty project to fail unexpectedly with ImportError in `template/.../pipeline.py`.
* Fixed bug related to saving dataframe with categorical variables in table mode using `HDFS3DataSet`.
* Fixed bug that caused unexpected behavior when using `from_nodes` and `to_nodes` in pipelines using transcoding.
* Credentials nested in the dataset config are now also resolved correctly.
* Bumped minimum required pandas version to 0.24.0 to make use of `pandas.DataFrame.to_numpy` (recommended alternative to `pandas.DataFrame.values`).
* Docs improvements.
* `Pipeline.transform` skips modifying node inputs/outputs containing `params:` or `parameters` keywords.
* Support for `dataset_credentials` key in the credentials for `PartitionedDataSet` is now deprecated. The dataset credentials should be specified explicitly inside the dataset config.
* Datasets can have a new `confirm` function which is called after a successful node function execution if the node contains `confirms` argument with such dataset name.
* Make the resume prompt on pipeline run failure use `--from-nodes` instead of `--from-inputs` to avoid unnecessarily re-running nodes that had already executed.
* When closed, Jupyter notebook kernels are automatically terminated after 30 seconds of inactivity by default. Use `--idle-timeout` option to update it.
* Added `kedro-viz` to the Kedro project template `requirements.txt` file.
* Removed the `results` and `references` folder from the project template.
* Updated contribution process in `CONTRIBUTING.md`.

## Breaking changes to the API
* Existing `MatplotlibWriter` dataset in `contrib` was renamed to `MatplotlibLocalWriter`.
* `kedro/contrib/io/matplotlib/matplotlib_writer.py` was renamed to `kedro/contrib/io/matplotlib/matplotlib_local_writer.py`.
* `kedro.contrib.io.bioinformatics.sequence_dataset.py` was renamed to `kedro.contrib.io.bioinformatics.biosequence_local_dataset.py`.

## Thanks for supporting contributions
[Andrii Ivaniuk](https://github.com/andrii-ivaniuk), [Jonas Kemper](https://github.com/jonasrk), [Yuhao Zhu](https://github.com/yhzqb), [Balazs Konig](https://github.com/BalazsKonigQB), [Pedro Abreu](https://github.com/PedroAbreuQB), [Tam-Sanh Nguyen](https://github.com/tamsanh), [Peter Zhao](https://github.com/zxpeter), [Deepyaman Datta](https://github.com/deepyaman), [Florian Roessler](https://github.com/fdroessler/), [Miguel Rodriguez Gutierrez](https://github.com/MigQ2)

# 0.15.5

## Major features and improvements
* New CLI commands and command flags:
  - Load multiple `kedro run` CLI flags from a configuration file with the `--config` flag (e.g. `kedro run --config run_config.yml`)
  - Run parametrised pipeline runs with the `--params` flag (e.g. `kedro run --params param1:value1,param2:value2`).
  - Lint your project code using the `kedro lint` command, your project is linted with [`black`](https://github.com/psf/black) (Python 3.6+), [`flake8`](https://gitlab.com/pycqa/flake8) and [`isort`](https://github.com/timothycrosley/isort).
* Load specific environments with Jupyter notebooks using `KEDRO_ENV` which will globally set `run`, `jupyter notebook` and `jupyter lab` commands using environment variables.
* Added the following datasets:
  - `CSVGCSDataSet` dataset in `contrib` for working with CSV files in Google Cloud Storage.
  - `ParquetGCSDataSet` dataset in `contrib` for working with Parquet files in Google Cloud Storage.
  - `JSONGCSDataSet` dataset in `contrib` for working with JSON files in Google Cloud Storage.
  - `MatplotlibS3Writer` dataset in `contrib` for saving Matplotlib images to S3.
  - `PartitionedDataSet` for working with datasets split across multiple files.
  - `JSONDataSet` dataset for working with JSON files that uses [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to communicate with the underlying filesystem. It doesn't support `http(s)` protocol for now.
* Added `s3fs_args` to all S3 datasets.
* Pipelines can be deducted with `pipeline1 - pipeline2`.

## Bug fixes and other changes
* `ParallelRunner` now works with `SparkDataSet`.
* Allowed the use of nulls in `parameters.yml`.
* Fixed an issue where `%reload_kedro` wasn't reloading all user modules.
* Fixed `pandas_to_spark` and `spark_to_pandas` decorators to work with functions with kwargs.
* Fixed a bug where `kedro jupyter notebook` and `kedro jupyter lab` would run a different Jupyter installation to the one in the local environment.
* Implemented Databricks-compatible dataset versioning for `SparkDataSet`.
* Fixed a bug where `kedro package` would fail in certain situations where `kedro build-reqs` was used to generate `requirements.txt`.
* Made `bucket_name` argument optional for the following datasets: `CSVS3DataSet`, `HDFS3DataSet`, `PickleS3DataSet`, `contrib.io.parquet.ParquetS3DataSet`, `contrib.io.gcs.JSONGCSDataSet` - bucket name can now be included into the filepath along with the filesystem protocol (e.g. `s3://bucket-name/path/to/key.csv`).
* Documentation improvements and fixes.

## Breaking changes to the API
* Renamed entry point for running pip-installed projects to `run_package()` instead of `main()` in `src/<package>/run.py`.
* `bucket_name` key has been removed from the string representation of the following datasets: `CSVS3DataSet`, `HDFS3DataSet`, `PickleS3DataSet`, `contrib.io.parquet.ParquetS3DataSet`, `contrib.io.gcs.JSONGCSDataSet`.
* Moved the `mem_profiler` decorator to `contrib` and separated the `contrib` decorators so that dependencies are modular. You may need to update your import paths, for example the pyspark decorators should be imported as `from kedro.contrib.decorators.pyspark import <pyspark_decorator>` instead of `from kedro.contrib.decorators import <pyspark_decorator>`.

## Thanks for supporting contributions
[Sheldon Tsen](https://github.com/sheldontsen-qb), [@roumail](https://github.com/roumail), [Karlson Lee](https://github.com/i25959341), [Waylon Walker](https://github.com/WaylonWalker), [Deepyaman Datta](https://github.com/deepyaman), [Giovanni](https://github.com/plauto), [Zain Patel](https://github.com/mzjp2)

# 0.15.4

## Major features and improvements
* `kedro jupyter` now gives the default kernel a sensible name.
* `Pipeline.name` has been deprecated in favour of `Pipeline.tags`.
* Reuse pipelines within a Kedro project using `Pipeline.transform`, it simplifies dataset and node renaming.
* Added Jupyter Notebook line magic (`%run_viz`) to run `kedro viz` in a Notebook cell (requires [`kedro-viz`](https://github.com/quantumblacklabs/kedro-viz) version 3.0.0 or later).
* Added the following datasets:
  - `NetworkXLocalDataSet` in `kedro.contrib.io.networkx` to load and save local graphs (JSON format) via NetworkX. (by [@josephhaaga](https://github.com/josephhaaga))
  - `SparkHiveDataSet` in `kedro.contrib.io.pyspark.SparkHiveDataSet` allowing usage of Spark and insert/upsert on non-transactional Hive tables.
* `kedro.contrib.config.TemplatedConfigLoader` now supports name/dict key templating and default values.

## Bug fixes and other changes
* `get_last_load_version()` method for versioned datasets now returns exact last load version if the dataset has been loaded at least once and `None` otherwise.
* Fixed a bug in `_exists` method for versioned `SparkDataSet`.
* Enabled the customisation of the ExcelWriter in `ExcelLocalDataSet` by specifying options under `writer` key in `save_args`.
* Fixed a bug in IPython startup script, attempting to load context from the incorrect location.
* Removed capping the length of a dataset's string representation.
* Fixed `kedro install` command failing on Windows if `src/requirements.txt` contains a different version of Kedro.
* Enabled passing a single tag into a node or a pipeline without having to wrap it in a list (i.e. `tags="my_tag"`).

## Breaking changes to the API
* Removed `_check_paths_consistency()` method from `AbstractVersionedDataSet`. Version consistency check is now done in `AbstractVersionedDataSet.save()`. Custom versioned datasets should modify `save()` method implementation accordingly.

## Thanks for supporting contributions
[Joseph Haaga](https://github.com/josephhaaga), [Deepyaman Datta](https://github.com/deepyaman), [Joost Duisters](https://github.com/JoostDuisters), [Zain Patel](https://github.com/mzjp2), [Tom Vigrass](https://github.com/tomvigrass)

# 0.15.3

## Bug Fixes and other changes
* Narrowed the requirements for `PyTables` so that we maintain support for Python 3.5.

# 0.15.2

## Major features and improvements
* Added `--load-version`, a `kedro run` argument that allows you run the pipeline with a particular load version of a dataset.
* Support for modular pipelines in `src/`, break the pipeline into isolated parts with reusability in mind.
* Support for multiple pipelines, an ability to have multiple entry point pipelines and choose one with `kedro run --pipeline NAME`.
* Added a `MatplotlibWriter` dataset in `contrib` for saving Matplotlib images.
* An ability to template/parameterize configuration files with `kedro.contrib.config.TemplatedConfigLoader`.
* Parameters are exposed as a context property for ease of access in iPython / Jupyter Notebooks with `context.params`.
* Added `max_workers` parameter for ``ParallelRunner``.

## Bug fixes and other changes
* Users will override the `_get_pipeline` abstract method in `ProjectContext(KedroContext)` in `run.py` rather than the `pipeline` abstract property. The `pipeline` property is not abstract anymore.
* Improved an error message when versioned local dataset is saved and unversioned path already exists.
* Added `catalog` global variable to `00-kedro-init.py`, allowing you to load datasets with `catalog.load()`.
* Enabled tuples to be returned from a node.
* Disallowed the ``ConfigLoader`` loading the same file more than once, and deduplicated the `conf_paths` passed in.
* Added a `--open` flag to `kedro build-docs` that opens the documentation on build.
* Updated the ``Pipeline`` representation to include name of the pipeline, also making it readable as a context property.
* `kedro.contrib.io.pyspark.SparkDataSet` and `kedro.contrib.io.azure.CSVBlobDataSet` now support versioning.

## Breaking changes to the API
* `KedroContext.run()` no longer accepts `catalog` and `pipeline` arguments.
* `node.inputs` now returns the node's inputs in the order required to bind them properly to the node's function.

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman), [Luciano Issoe](https://github.com/Lucianois), [Joost Duisters](https://github.com/JoostDuisters), [Zain Patel](https://github.com/mzjp2), [William Ashford](https://github.com/williamashfordQB), [Karlson Lee](https://github.com/i25959341)

# 0.15.1

## Major features and improvements
* Extended `versioning` support to cover the tracking of environment setup, code and datasets.
* Added the following datasets:
  - `FeatherLocalDataSet` in `contrib` for usage with pandas. (by [@mdomarsaleem](https://github.com/mdomarsaleem))
* Added `get_last_load_version` and `get_last_save_version` to `AbstractVersionedDataSet`.
* Implemented `__call__` method on `Node` to allow for users to execute `my_node(input1=1, input2=2)` as an alternative to `my_node.run(dict(input1=1, input2=2))`.
* Added new `--from-inputs` run argument.

## Bug fixes and other changes
* Fixed a bug in `load_context()` not loading context in non-Kedro Jupyter Notebooks.
* Fixed a bug in `ConfigLoader.get()` not listing nested files for `**`-ending glob patterns.
* Fixed a logging config error in Jupyter Notebook.
* Updated documentation in `03_configuration` regarding how to modify the configuration path.
* Documented the architecture of Kedro showing how we think about library, project and framework components.
* `extras/kedro_project_loader.py` renamed to `extras/ipython_loader.py` and now runs any IPython startup scripts without relying on the Kedro project structure.
* Fixed TypeError when validating partial function's signature.
* After a node failure during a pipeline run, a resume command will be suggested in the logs. This command will not work if the required inputs are MemoryDataSets.

## Breaking changes to the API

## Thanks for supporting contributions
[Omar Saleem](https://github.com/mdomarsaleem), [Mariana Silva](https://github.com/marianansilva), [Anil Choudhary](https://github.com/aniryou), [Craig](https://github.com/cfranklin11)

# 0.15.0

## Major features and improvements
* Added `KedroContext` base class which holds the configuration and Kedro's main functionality (catalog, pipeline, config, runner).
* Added a new CLI command `kedro jupyter convert` to facilitate converting Jupyter Notebook cells into Kedro nodes.
* Added support for `pip-compile` and new Kedro command `kedro build-reqs` that generates `requirements.txt` based on `requirements.in`.
* Running `kedro install` will install packages to conda environment if `src/environment.yml` exists in your project.
* Added a new `--node` flag to `kedro run`, allowing users to run only the nodes with the specified names.
* Added new `--from-nodes` and `--to-nodes` run arguments, allowing users to run a range of nodes from the pipeline.
* Added prefix `params:` to the parameters specified in `parameters.yml` which allows users to differentiate between their different parameter node inputs and outputs.
* Jupyter Lab/Notebook now starts with only one kernel by default.
* Added the following datasets:
  -  `CSVHTTPDataSet` to load CSV using HTTP(s) links.
  - `JSONBlobDataSet` to load json (-delimited) files from Azure Blob Storage.
  - `ParquetS3DataSet` in `contrib` for usage with pandas. (by [@mmchougule](https://github.com/mmchougule))
  - `CachedDataSet` in `contrib` which will cache data in memory to avoid io/network operations. It will clear the cache once a dataset is no longer needed by a pipeline. (by [@tsanikgr](https://github.com/tsanikgr))
  - `YAMLLocalDataSet` in `contrib` to load and save local YAML files. (by [@Minyus](https://github.com/Minyus))

## Bug fixes and other changes
* Documentation improvements including instructions on how to initialise a Spark session using YAML configuration.
* `anyconfig` default log level changed from `INFO` to `WARNING`.
* Added information on installed plugins to `kedro info`.
* Added style sheets for project documentation, so the output of `kedro build-docs` will resemble the style of `kedro docs`.

## Breaking changes to the API
* Simplified the Kedro template in `run.py` with the introduction of `KedroContext` class.
* Merged `FilepathVersionMixIn` and `S3VersionMixIn` under one abstract class `AbstractVersionedDataSet` which extends`AbstractDataSet`.
* `name` changed to be a keyword-only argument for `Pipeline`.
* `CSVLocalDataSet` no longer supports URLs. `CSVHTTPDataSet` supports URLs.

### Migration guide from Kedro 0.14.* to Kedro 0.15.0
#### Migration for Kedro project template
This guide assumes that:
  * The framework specific code has not been altered significantly
  * Your project specific code is stored in the dedicated python package under `src/`.

The breaking changes were introduced in the following project template files:
- `<project-name>/.ipython/profile_default/startup/00-kedro-init.py`
- `<project-name>/kedro_cli.py`
- `<project-name>/src/tests/test_run.py`
- `<project-name>/src/<package-name>/run.py`
- `<project-name>/.kedro.yml` (new file)

The easiest way to migrate your project from Kedro 0.14.* to Kedro 0.15.0 is to create a new project (by using `kedro new`) and move code and files bit by bit as suggested in the detailed guide below:

1. Create a new project with the same name by running `kedro new`

2. Copy the following folders to the new project:
 - `results/`
 - `references/`
 - `notebooks/`
 - `logs/`
 - `data/`
 - `conf/`

3. If you customised your `src/<package>/run.py`, make sure you apply the same customisations to `src/<package>/run.py`
 - If you customised `get_config()`, you can override `config_loader` property in `ProjectContext` derived class
 - If you customised `create_catalog()`, you can override `catalog()` property in `ProjectContext` derived class
 - If you customised `run()`, you can override `run()` method in `ProjectContext` derived class
 - If you customised default `env`, you can override it in `ProjectContext` derived class or pass it at construction. By default, `env` is `local`.
 - If you customised default `root_conf`, you can override `CONF_ROOT` attribute in `ProjectContext` derived class. By default, `KedroContext` base class has `CONF_ROOT` attribute set to `conf`.

4. The following syntax changes are introduced in ipython or Jupyter notebook/labs:
 - `proj_dir` -> `context.project_path`
 - `proj_name` -> `context.project_name`
 - `conf` -> `context.config_loader`.
 - `io` -> `context.catalog` (e.g., `io.load()` -> `context.catalog.load()`)

5. If you customised your `kedro_cli.py`, you need to apply the same customisations to your `kedro_cli.py` in the new project.

6. Copy the contents of the old project's `src/requirements.txt` into the new project's `src/requirements.in` and, from the project root directory, run the `kedro build-reqs` command in your terminal window.

#### Migration for versioning custom dataset classes

If you defined any custom dataset classes which support versioning in your project, you need to apply the following changes:

1. Make sure your dataset inherits from `AbstractVersionedDataSet` only.
2. Call `super().__init__()` with the appropriate arguments in the dataset's `__init__`. If storing on local filesystem, providing the filepath and the version is enough. Otherwise, you should also pass in an `exists_function` and a `glob_function` that emulate `exists` and `glob` in a different filesystem (see `CSVS3DataSet` as an example).
3. Remove setting of the `_filepath` and `_version` attributes in the dataset's `__init__`, as this is taken care of in the base abstract class.
4. Any calls to `_get_load_path` and `_get_save_path` methods should take no arguments.
5. Ensure you convert the output of `_get_load_path` and `_get_save_path` appropriately, as these now return [`PurePath`s](https://docs.python.org/3/library/pathlib.html#pure-paths) instead of strings.
6. Make sure `_check_paths_consistency` is called with [`PurePath`s](https://docs.python.org/3/library/pathlib.html#pure-paths) as input arguments, instead of strings.

These steps should have brought your project to Kedro 0.15.0. There might be some more minor tweaks needed as every project is unique, but now you have a pretty solid base to work with. If you run into any problems, please consult the [Kedro documentation](https://kedro.readthedocs.io).

## Thanks for supporting contributions
[Dmitry Vukolov](https://github.com/dvukolov), [Jo Stichbury](https://github.com/stichbury), [Angus Williams](https://github.com/awqb), [Deepyaman Datta](https://github.com/deepyaman), [Mayur Chougule](https://github.com/mmchougule), [Marat Kopytjuk](https://github.com/kopytjuk), [Evan Miller](https://github.com/evanmiller29), [Yusuke Minami](https://github.com/Minyus)

# 0.14.3

## Major features and improvements
* Tab completion for catalog datasets in `ipython` or `jupyter` sessions. (Thank you [@datajoely](https://github.com/datajoely) and [@WaylonWalker](https://github.com/WaylonWalker))
* Added support for transcoding, an ability to decouple loading/saving mechanisms of a dataset from its storage location, denoted by adding '@' to the dataset name.
* Datasets have a new `release` function that instructs them to free any cached data. The runners will call this when the dataset is no longer needed downstream.

## Bug fixes and other changes
* Add support for pipeline nodes made up from partial functions.
* Expand user home directory `~` for TextLocalDataSet (see issue #19).
* Add a `short_name` property to `Node`s for a display-friendly (but not necessarily unique) name.
* Add Kedro project loader for IPython: `extras/kedro_project_loader.py`.
* Fix source file encoding issues with Python 3.5 on Windows.
* Fix local project source not having priority over the same source installed as a package, leading to local updates not being recognised.

## Breaking changes to the API
* Remove the max_loads argument from the `MemoryDataSet` constructor and from the `AbstractRunner.create_default_data_set` method.

## Thanks for supporting contributions
[Joel Schwarzmann](https://github.com/datajoely), [Alex Kalmikov](https://github.com/kalexqb)

# 0.14.2

## Major features and improvements
* Added Data Set transformer support in the form of AbstractTransformer and DataCatalog.add_transformer.

## Breaking changes to the API
* Merged the `ExistsMixin` into `AbstractDataSet`.
* `Pipeline.node_dependencies` returns a dictionary keyed by node, with sets of parent nodes as values; `Pipeline` and `ParallelRunner` were refactored to make use of this for topological sort for node dependency resolution and running pipelines respectively.
* `Pipeline.grouped_nodes` returns a list of sets, rather than a list of lists.

## Thanks for supporting contributions

[Darren Gallagher](https://github.com/dazzag24), [Zain Patel](https://github.com/mzjp2)

# 0.14.1

## Major features and improvements
* New I/O module `HDFS3DataSet`.

## Bug fixes and other changes
* Improved API docs.
* Template `run.py` will throw a warning instead of error if `credentials.yml`
  is not present.

## Breaking changes to the API
None


# 0.14.0

The initial release of Kedro.


## Thanks for supporting contributions

Jo Stichbury, Aris Valtazanos, Fabian Peters, Guilherme Braccialli, Joel Schwarzmann, Miguel Beltre, Mohammed ElNabawy, Deepyaman Datta, Shubham Agrawal, Oleg Andreyev, Mayur Chougule, William Ashford, Ed Cannon, Nikhilesh Nukala, Sean Bailey, Vikram Tegginamath, Thomas Huijskens, Musa Bilal

We are also grateful to everyone who advised and supported us, filed issues or helped resolve them, asked and answered questions and were part of inspiring discussions.
