# Upcoming Release

## Major features and improvements
* Added `KedroDataCatalog.filter()` to filter datasets by name and type.
* Added `Pipeline.grouped_nodes_by_namespace` property which returns a dictionary of nodes grouped by namespace, intended to be used by plugins to facilitate deployment of namespaced nodes together.

## Bug fixes and other changes
* Added `DataCatalog` deprecation warning.
* Updated `_LazyDataset` representation when printing `KedroDataCatalog`.
* Fixed `MemoryDataset` to infer `assign` copy mode for Ibis Tables, which previously would be inferred as `deepcopy`.
* Fixed pipeline packaging issue by ensuring `pipelines/__init__.py` exists when creating new pipelines.
* Changed the execution of `SequentialRunner` to not use an executor pool to ensure it's single threaded.
* Fixed `%load_node` magic command to work with Jupyter Notebook `>=7.2.0`.
* Remove `7: Kedro Viz` from Kedro tools.

## Breaking changes to the API
## Documentation changes
* Added documentation for Kedro's support for Delta Lake versioning.
* Added documentation for Kedro's support for Iceberg versioning.
* Added documentation for Kedro's nodes grouping in deployment.
* Fixed a minor grammatical error in Kedro-Viz installation instructions to improve documentation clarity.

# Release 0.19.11

## Major features and improvements
* Implemented `KedroDataCatalog.to_config()` method that converts the catalog instance into a configuration format suitable for serialization.
* Improve OmegaConfigLoader performance.
* Replaced `trufflehog` with `detect-secrets` for detecting secrets within a code base.
* Added support for `%load_ext kedro`.

## Bug fixes and other changes
* Added validation to ensure dataset versions consistency across catalog.
* Fixed a bug in project creation when using a custom starter template offline.
* Added `node` import to the pipeline template.
* Update error message when executing kedro run without pipeline.
* Safeguard hooks when user incorrectly registers a hook class in settings.py.
* Fixed parsing paths with query and fragment.
* Remove lowercase transformation in regex validation.
* Moved `kedro-catalog` JSON schema to `kedro-datasets`.
* Updated `Partitioned dataset lazy saving` docs page.
* Fixed `KedroDataCatalog` mutation after pipeline run.
* Made `KedroDataCatalog._datasets` compatible with `DataCatalog._datasets`.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [Hendrik Scherner](https://github.com/SchernHe)
* [Chris Schopp](https://github.com/chrisschopp)

# Release 0.19.10

## Major features and improvements
* Add official support for Python 3.13.
* Implemented dict-like interface for `KedroDataCatalog`.
* Implemented lazy dataset initializing for `KedroDataCatalog`.
* Project dependencies on both the default template and on starter templates are now explicitly declared on the `pyproject.toml` file, allowing Kedro projects to work with project management tools like `uv`, `pdm`, and `rye`.

**Note:** ``KedroDataCatalog`` is an experimental feature and is under active development. Therefore, it is possible we'll introduce breaking changes to this class, so be mindful of that if you decide to use it already. Let us know if you have any feedback about the ``KedroDataCatalog`` or ideas for new features.

## Bug fixes and other changes
* Added I/O support for Oracle Cloud Infrastructure (OCI) Object Storage filesystem.
* Fixed `DatasetAlreadyExistsError` for `ThreadRunner` when Kedro project run and using runner separately.

## Breaking changes to the API
## Documentation changes
* Added Databricks Asset Bundles deployment guide.
* Added a new minimal Kedro project creation guide.
* Added example to explain how dataset factories work.
* Updated CLI autocompletion docs with new Click syntax.
* Standardised `.parquet` suffix in docs and tests.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [G. D. McBain](https://github.com/gdmcbain)
* [Greg Vaslowski](https://github.com/Vaslo)
* [Hyewon Choi](https://github.com/hyew0nChoi)
* [Pedro Antonacio](https://github.com/antonacio)

# Release 0.19.9

## Major features and improvements
* Dropped Python 3.8 support.
* Implemented `KedroDataCatalog` repeating `DataCatalog` functionality with a few API enhancements:
  * Removed `_FrozenDatasets` and access datasets as properties;
  * Added get dataset by name feature;
  * `add_feed_dict()` was simplified to only add raw data;
  * Datasets' initialisation was moved out from `from_config()` method to the constructor.
* Moved development requirements from `requirements.txt` to the dedicated section in `pyproject.toml` for project template.
* Implemented `Protocol` abstraction for the current `DataCatalog` and adding new catalog implementations.
* Refactored `kedro run` and `kedro catalog` commands.
* Moved pattern resolution logic from `DataCatalog` to a separate component - `CatalogConfigResolver`. Updated `DataCatalog` to use `CatalogConfigResolver` internally.
* Made packaged Kedro projects return `session.run()` output to be used when running it in the interactive environment.
* Enhanced `OmegaConfigLoader` configuration validation to detect duplicate keys at all parameter levels, ensuring comprehensive nested key checking.

**Note:** ``KedroDataCatalog`` is an experimental feature and is under active development. Therefore, it is possible we'll introduce breaking changes to this class, so be mindful of that if you decide to use it already. Let us know if you have any feedback about the ``KedroDataCatalog`` or ideas for new features.

## Bug fixes and other changes
* Fixed bug where using dataset factories breaks with `ThreadRunner`.
* Fixed a bug where `SharedMemoryDataset.exists` would not call the underlying `MemoryDataset`.
* Fixed template projects example tests.
* Made credentials loading consistent between `KedroContext._get_catalog()` and `resolve_patterns` so that both use `_get_config_credentials()`

## Breaking changes to the API
* Removed `ShelveStore` to address a security vulnerability.

## Documentation changes
* Fix logo on PyPI page.
* Minor language/styling updates.


## Community contributions
* [Puneet](https://github.com/puneeter)
* [ethanknights](https://github.com/ethanknights)
* [Manezki](https://github.com/Manezki)
* [MigQ2](https://github.com/MigQ2)
* [Felix Scherz](https://github.com/felixscherz)
* [Yu-Sheng Li](https://github.com/kevin1kevin1k)

# Release 0.19.8

## Major features and improvements
* Made default run entrypoint in `__main__.py` work in interactive environments such as IPyhon and Databricks.

## Bug fixes and other changes
* Fixed a bug that caused tracebacks disappeared from CLI runs.
* Moved `_find_run_command()` and `_find_run_command_in_plugins()` from `__main__.py` in the project template to the framework itself.
* Fixed a bug where `%load_node` breaks with multi-lines import statements.
* Fixed a regression where `rich` mark up logs stop showing since 0.19.7.

## Breaking changes to the API

## Documentation changes
* Add clarifications in docs explaining how runtime parameter resolution works.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [cclauss](https://github.com/cclauss)
* [eltociear](https://github.com/eltociear)
* [ltalirz](https://github.com/ltalirz)

# Release 0.19.7

## Major features and improvements
* Exposed `load` and `save` publicly for each dataset in the core `kedro` library, and enabled other datasets to do the same. If a dataset doesn't expose `load` or `save` publicly, Kedro will fall back to using `_load` or `_save`, respectively.
* Kedro commands are now lazily loaded to add performance gains when running Kedro commands.
* Implemented key completion support for accessing datasets in the `DataCatalog`.
* Implemented dataset pretty printing.
* Implemented `DataCatalog` pretty printing.
* Moved to an opt-out model for telemetry, enabling it by default without requiring prior consent.

## Bug fixes and other changes
* Updated error message for invalid catalog entries.
* Updated error message for catalog entries when the dataset class is not found with hints on how to resolve the issue.
* Fixed a bug in the `DataCatalog` `shallow_copy()` method to ensure it returns the type of the used catalog and doesn't cast it to `DataCatalog`.
* Made [kedro-telemetry](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry) a core dependency.
* Fixed a bug when `OmegaConfigLoader` is printed, there are few missing arguments.
* Fixed a bug when where iterating `OmegaConfigLoader`'s `keys` return empty dictionary.

## Breaking changes to the API

## Upcoming deprecations for Kedro 0.20.0
* The utility method `get_pkg_version()` is deprecated and will be removed in Kedro 0.20.0.
* `LambdaDataset` is deprecated and will be removed in Kedro 0.20.0.

## Documentation changes
* Improved documentation for configuring dataset parameters in the data catalog
* Extended documentation with an example of logging customisation at runtime

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [nickolasrm](https://github.com/nickolasrm)
* [yury-fedotov](https://github.com/yury-fedotov)

# Release 0.19.6

## Major features and improvements
* Added `raise_errors` argument to `find_pipelines`. If `True`, the first pipeline for which autodiscovery fails will cause an error to be raised. The default behaviour is still to raise a warning for each failing pipeline.
* It is now possible to use Kedro without having `rich` installed.
* Updated custom logging behavior: `conf/logging.yml` will be used if it exists and `KEDRO_LOGGING_CONFIG` is not set; otherwise, `default_logging.yml` will be used.

## Bug fixes and other changes
* User defined catch-all dataset factory patterns now override the default pattern provided by the runner.

## Breaking changes to the API

## Upcoming deprecations for Kedro 0.20.0
* All micro-packaging commands (`kedro micropkg pull`, `kedro micropkg package`) are deprecated and will be removed in Kedro 0.20.0.

## Documentation changes
* Improved documentation for custom starters
* Added a new docs section on deploying Kedro project on AWS Airflow MWAA
* Detailed instructions on using `globals` and `runtime_params` with the `OmegaConfigLoader`

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [doxenix](https://github.com/doxenix)
* [cleeeks](https://github.com/cleeeks)

# Release 0.19.5

## Bug fixes and other changes
* Fixed breaking import issue when working on a project with `kedro-viz` on python 3.8.

## Documentation changes
* Updated the documentation for deploying a Kedro project with Astronomer Airflow.
* Used `kedro-sphinx-theme` for documentation.
* Add mentions about correct usage of `configure_project` with `multiprocessing`.
*
# Release 0.19.4

## Major features and improvements
* Kedro commands now work from any subdirectory within a Kedro project.
* Kedro CLI now provides a better error message when project commands are run outside of a project i.e. `kedro run`
* Added the `--telemetry` flag to `kedro new`, allowing the user to register consent to have user analytics collected at the same time as the project is created.
* Improved the performance of `Pipeline` object creation and summing.
* Improved suggestions to resume failed pipeline runs.
* Dropped the dependency on `toposort` in favour of the built-in `graphlib` module.
* Cookiecutter errors are shown in short format without the `--verbose` flag.

## Bug fixes and other changes
* Updated `kedro pipeline create` and `kedro pipeline delete` to read the base environment from the project settings.
* Updated CLI command `kedro catalog resolve` to read credentials properly.
* Changed the path of where pipeline tests generated with `kedro pipeline create` from `<project root>/src/tests/pipelines/<pipeline name>` to `<project root>/tests/pipelines/<pipeline name>`.
* Updated ``.gitignore`` to prevent pushing MLflow local runs folder to a remote forge when using MLflow and Git.
* Fixed error handling message for malformed yaml/json files in OmegaConfigLoader.
* Fixed a bug in `node`-creation allowing self-dependencies when using transcoding, that is datasets named like `name@format`.
* Improved error message when passing wrong value to node.

## Breaking changes to the API
* Methods `_is_project` and `_find_kedro_project` have been moved to `kedro.utils`. We recommend not using private methods in your code, but if you do, please update your code to use the new location.

## Documentation changes
* Added missing description for `merge_strategy` argument in OmegaConfigLoader.
* Added documentation on best practices for testing nodes and pipelines.
* Clarified docs around using custom resolvers without a full Kedro project.


## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [ondrejzacha](https://github.com/ondrejzacha)
* [Puneet](https://github.com/puneeter)

# Release 0.19.3

## Major features and improvements
* Create the debugging line magic `%load_node` for Jupyter Notebook and Jupyter Lab.
* Add official support for Python 3.12.
* Add better IPython, VS Code Notebook support for `%load_node` and minimal support for Databricks.
* Add full Kedro Node input syntax for `%load_node`.

## Bug fixes and other changes
* Updated CLI Command `kedro catalog resolve` to work with dataset factories that use `PartitionedDataset`.
* Addressed arbitrary file write via archive extraction security vulnerability in micropackaging.
* Added the `_EPHEMERAL` attribute to `AbstractDataset` and other Dataset classes that inherit from it.
* Added new JSON Schema that works with Kedro versions 0.19.*

## Breaking changes to the API

## Documentation changes
* Enable read-the-docs search when user presses Command/Ctrl + K.
* Added documentation for `kedro-telemetry` and the data collected by it.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [MosaicMan](https://github.com/MosaicMan)
* [Fazil](https://github.com/lordsoffallen)

# Release 0.19.2

## Bug fixes and other changes
* Removed example pipeline requirements when examples are not selected in `tools`.
* Allowed modern versions of JupyterLab and Jupyter Notebooks.
* Removed setuptools dependency
* Added `source_dir` explicitly in `pyproject.toml` for non-src layout project.
* `MemoryDataset` entries are now included in free outputs.
* Removed black dependency and replaced it functionality with `ruff format`.

## Breaking changes to the API
* Added logging about not using async mode in `SequentiallRunner` and `ParallelRunner`.
* Changed input format for tools option obtained from --config file from numbers to short names.

## Documentation changes
* Added documentation about `bootstrap_project` and `configure_project`.
* Added documentation about `kedro run` and hook execution order.

## Migration guide from Kedro 0.18.* to 0.19.*
[See the migration guide for 0.19 in the Kedro documentation](https://docs.kedro.org/en/latest/resources/migration.html).

# Release 0.19.1

## Bug fixes and other changes
* Loosened pin for `kedro-telemetry` to fix dependency issues in `0.19.0`.

## Migration guide from Kedro 0.18.* to 0.19.*
[See the migration guide for 0.19 in the Kedro documentation](https://docs.kedro.org/en/latest/resources/migration.html).


# Release 0.19.0

## Major features and improvements
* Dropped Python 3.7 support.
* [Introduced project tools and example to the `kedro new` CLI flow](docs/source/get_started/new_project.md#project-tools).
* The new spaceflights starters, `spaceflights-pandas`, `spaceflights-pandas-viz`, `spaceflights-pyspark`, and `spaceflights-pyspark-viz` can be used with the `kedro new` command with the `--starter` flag.
* Added the `--conf-source` option to `%reload_kedro`, allowing users to specify a source for project configuration.
* [Added the functionality to choose a merging strategy for config files loaded with `OmegaConfigLoader`](docs/source/configuration/advanced_configuration.md#how-to-change-the-merge-strategy-used-by-omegaconfigloader).
* Modified the mechanism of importing datasets, raise more explicit error when dependencies are missing.
* Added validation for configuration file used to override run commands via the CLI.
* Moved the default environment `base` and `local` from config loader to `_ProjectSettings`. This enables the use of config loader as a standalone class without affecting existing Kedro Framework users.

## Bug fixes and other changes
* Added a new field `tools` to `pyproject.toml` when a project is created.
* Reduced `spaceflights` data to minimise waiting times during tutorial execution.
* Added validation to node tags to be consistent with node names.
* Removed `pip-tools` as a dependency.
* Accepted path-like filepaths more broadly for datasets.
* Removed support for defining the `layer` attribute at top-level within DataCatalog.
* Bumped `kedro-datasets` to latest `2.0.0`.

## Breaking changes to the API
* Renamed the `data_sets` argument and the `_data_sets` attribute in `Catalog` and their references to `datasets` and `_datasets` respectively.
* Renamed the `data_sets()` method in `Pipeline` and all references to it to `datasets()`.
* Renamed all other uses of `data_set` and `data_sets` in the codebase to `dataset` and `datasets` respectively.
* Remove deprecated `project_version` from `ProjectMetadata`.
* Removed `package_name` argument from `KedroSession.create`.
* Removed the `create_default_data_set()` method in the `Runner` in favour of using dataset factories to create default dataset instances.
* Removed `layer` argument from the DataCatalog.

### Datasets
* Removed `kedro.extras.datasets` and tests.
* Reduced constructor arguments for `APIDataset` by replacing most arguments with a single constructor argument `load_args`. This makes it more consistent with other Kedro DataSets and the underlying `requests` API, and automatically enables the full configuration domain: stream, certificates, proxies, and more.
* Removed `PartitionedDataset` and `IncrementalDataset` from `kedro.io`

### CLI
* Removed deprecated commands:
   * `kedro docs`
   * `kedro jupyter convert`
   * `kedro activate-nbstripout`
   * `kedro build-docs`
   * `kedro build-reqs`
   * `kedro lint`
   * `kedro test`
* Added the `--addons` flag to the `kedro new` command.
* Added the `--name` flag to the `kedro new` command.
* Removed `kedro run` flags `--node`, `--tag`, and `--load-version` in favour of `--nodes`, `--tags`, and `--load-versions`.

### ConfigLoader
* Made `OmegaConfigLoader` the default config loader.
* Removed `ConfigLoader` and `TemplatedConfigLoader`.
* `logging` is removed from `ConfigLoader` in favour of the environment variable `KEDRO_LOGGING_CONFIG`.

### Other
* Removed deprecated `kedro.extras.ColorHandler`.
* The Kedro IPython extension is no longer available as `%load_ext kedro.extras.extensions.ipython`; use `%load_ext kedro.ipython` instead.
* Anonymous nodes are given default names of the form `<function_name>([in1;in2;...]) -> [out1;out2;...]`, with the names of inputs and outputs separated by semicolons.
* The default project template now has one `pyproject.toml` at the root of the project (containing both the packaging metadata and the Kedro build config).
* The `requirements.txt` in the default project template moved to the root of the project as well (hence dependencies are now installed with `pip install -r requirements.txt` instead of `pip install -r src/requirements.txt`).
* The `spaceflights` starter has been renamed to `spaceflights-pandas`.
* The starters `pandas-iris`, `pyspark-iris`, `pyspark`, and `standalone-datacatalog` have been archived.

## Migration guide from Kedro 0.18.* to 0.19.*
[See the migration guide for 0.19 in the Kedro documentation](https://docs.kedro.org/en/latest/resources/migration.html).


### Logging
`logging.yml` is now independent of Kedro's run environment and only used if `KEDRO_LOGGING_CONFIG` is set to point to it.

## Community contributors
We are grateful to every community member who made a PR to Kedro that's found its way into 0.19.0, and give particular thanks to those who contributed between 0.18.14 and this release, either as part of their ongoing Kedro community involvement or as part of Hacktoberfest 2023 🎃

* [Jeroldine Akuye Oakley](https://github.com/JayOaks) 🎃
* [Laíza Milena Scheid Parizotto](https://github.com/laizaparizotto) 🎃
* [Mustapha Abdullahi](https://github.com/mustious)
* [Adam Kells](https://github.com/adamkells)
* [Ajay Gonepuri](https://github.com/HKABIG)

# Release 0.18.14

## Major features and improvements
* Allowed using of custom cookiecutter templates for creating pipelines with `--template` flag for `kedro pipeline create` or via `template/pipeline` folder.
* Allowed overriding of configuration keys with runtime parameters using the `runtime_params` resolver with `OmegaConfigLoader`.

## Bug fixes and other changes
* Updated dataset factories to resolve nested catalog config properly.
* Updated `OmegaConfigLoader` to handle paths containing dots outside of `conf_source`.
* Made `settings.py` optional.

## Documentation changes
* Added documentation to clarify execution order of hooks.
* Added a notebook example for spaceflights to illustrate how to incrementally add Kedro features.
* Moved documentation for the `standalone-datacatalog` starter into its [README file](https://github.com/kedro-org/kedro-starters/tree/main/standalone-datacatalog).
* Added new documentation about deploying a Kedro project with Amazon EMR.
* Added new documentation about how to publish a Kedro-Viz project to make it shareable.
* New TSC members added to the page and the organisation of each member is also now listed.
* Plus some minor bug fixes and changes across the documentation.

## Upcoming deprecations for Kedro 0.19.0
* All dataset classes will be removed from the core Kedro repository (`kedro.extras.datasets`). Install and import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
* All dataset classes ending with `DataSet` are deprecated and will be removed in Kedro `0.19.0` and `kedro-datasets` `2.0.0`. Instead, use the updated class names ending with `Dataset`.
* The starters `pandas-iris`, `pyspark-iris`, `pyspark`, and `standalone-datacatalog` are deprecated and will be archived in Kedro 0.19.0.
* `PartitionedDataset` and `IncrementalDataset` have been moved to `kedro-datasets` and will be removed in Kedro `0.19.0`. Install and import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:
* [Jason Hite](https://github.com/jasonmhite)
* [IngerMathilde](https://github.com/IngerMathilde)
* [Laíza Milena Scheid Parizotto](https://github.com/laizaparizotto)
* [Richard](https://github.com/CF-FHB-X)
* [flpvvvv](https://github.com/flpvvvv)
* [qheuristics](https://github.com/qheuristics)
* [Miguel Ortiz](https://github.com/miguel-ortiz-marin)
* [rxm7706](https://github.com/rxm7706)
* [Iñigo Hidalgo](https://github.com/inigohidalgo)
* [harmonys-qb](https://github.com/harmonys-qb)
* [Yi Kuang](https://github.com/lvxhnat)
* [Jens Lordén](https://github.com/Celsuss)

# Release 0.18.13

## Major features and improvements
* Added support for Python 3.11. This includes tackling challenges like dependency pinning and test adjustments to ensure a smooth experience. Detailed migration tips are provided below for further context.
* Added new `OmegaConfigLoader` features:
  * Allowed registering of custom resolvers to `OmegaConfigLoader` through `CONFIG_LOADER_ARGS`.
  * Added support for global variables to `OmegaConfigLoader`.
* Added `kedro catalog resolve` CLI command that resolves dataset factories in the catalog with any explicit entries in the project pipeline.
* Implemented a flat `conf/` structure for modular pipelines, and accordingly, updated the `kedro pipeline create` and `kedro catalog create` command.
* Updated new Kedro project template and Kedro starters:
  * Change Kedro starters and new Kedro projects to use `OmegaConfigLoader`.
  * Converted `setup.py` in new Kedro project template and Kedro starters to `pyproject.toml` and moved flake8 configuration
  to dedicated file `.flake8`.
  * Updated the spaceflights starter to use the new flat `conf/` structure.

## Bug fixes and other changes
* Updated `OmegaConfigLoader` to ignore config from hidden directories like `.ipynb_checkpoints`.

## Documentation changes
* Revised the `data` section to restructure beginner and advanced pages about the Data Catalog and datasets.
* Moved contributor documentation to the [GitHub wiki](https://github.com/kedro-org/kedro/wiki/Contribute-to-Kedro).
* Updated example of using generator functions in nodes.
* Added migration guide from the `ConfigLoader` and the `TemplatedConfigLoader` to the `OmegaConfigLoader`. The `ConfigLoader` and the `TemplatedConfigLoader` are deprecated and will be removed in the `0.19.0` release.

## Migration Tips for Python 3.11:
* PyTables on Windows: Users on Windows with Python >=3.8 should note we've pinned `pytables` to `3.8.0` due to compatibility issues.
* Spark Dependency: We've set an upper version limit for `pyspark` at <3.4 due to breaking changes in 3.4.
* Testing with Python 3.10: The latest `moto` version now supports parallel test execution for Python 3.10, resolving previous issues.

## Breaking changes to the API

## Upcoming deprecations for Kedro 0.19.0
* Renamed abstract dataset classes, in accordance with the [Kedro lexicon](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide#kedro-lexicon). Dataset classes ending with "DataSet" are deprecated and will be removed in 0.19.0. Note that all of the below classes are also importable from `kedro.io`; only the module where they are defined is listed as the location.

| Type                       | Deprecated Alias           | Location        |
| -------------------------- | -------------------------- | --------------- |
| `AbstractDataset`          | `AbstractDataSet`          | `kedro.io.core` |
| `AbstractVersionedDataset` | `AbstractVersionedDataSet` | `kedro.io.core` |

* Using the `layer` attribute at the top level is deprecated; it will be removed in Kedro version 0.19.0. Please move `layer` inside the `metadata` -> `kedro-viz` attributes.

## Community contributions
Thanks to [Laíza Milena Scheid Parizotto](https://github.com/laizaparizotto) and [Jonathan Cohen](https://github.com/JonathanDCohen).

# Release 0.18.12

## Major features and improvements
* Added dataset factories feature which uses pattern matching to reduce the number of catalog entries.
* Activated all built-in resolvers by default for `OmegaConfigLoader` except for `oc.env`.
* Added `kedro catalog rank` CLI command that ranks dataset factories in the catalog by matching priority.

## Bug fixes and other changes
* Consolidated dependencies and optional dependencies in `pyproject.toml`.
* Made validation of unique node outputs much faster.
* Updated `kedro catalog list` to show datasets generated with factories.

## Documentation changes
* Recommended `ruff` as the linter and removed mentions of `pylint`, `isort`, `flake8`.

## Community contributions
Thanks to [Laíza Milena Scheid Parizotto](https://github.com/laizaparizotto) and [Chris Schopp](https://github.com/cschopp-simwell).

## Breaking changes to the API

## Upcoming deprecations for Kedro 0.19.0
* `ConfigLoader` and `TemplatedConfigLoader` will be deprecated. Please use `OmegaConfigLoader` instead.

# Release 0.18.11

## Major features and improvements
* Added `databricks-iris` as an official starter.

## Bug fixes and other changes
* Reworked micropackaging workflow to use standard Python packaging practices.
* Make `kedro micropkg package` accept `--verbose`.
* Compare for protocol and delimiter in `PartitionedDataSet` to be able to pass the protocol to partitions which paths starts with the same characters as the protocol (e.g. `s3://s3-my-bucket`).

## Documentation changes
* Significant improvements to the documentation that covers working with Databricks and Kedro, including a new page for workspace-only development, and a guide to choosing the best workflow for your use case.
* Updated documentation for deploying with Prefect for version 2.0.
* Added documentation for developing a Kedro project using a Databricks workspace.

## Breaking changes to the API
* Logging is decoupled from `ConfigLoader`, use `KEDRO_LOGGING_CONFIG` to configure logging.

## Upcoming deprecations for Kedro 0.19.0
* Renamed dataset and error classes, in accordance with the [Kedro lexicon](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide#kedro-lexicon). Dataset classes ending with "DataSet" and error classes starting with "DataSet" are deprecated and will be removed in 0.19.0. Note that all of the below classes are also importable from `kedro.io`; only the module where they are defined is listed as the location.

| Type                        | Deprecated Alias            | Location                       |
| --------------------------- | --------------------------- | ------------------------------ |
| `CachedDataset`             | `CachedDataSet`             | `kedro.io.cached_dataset`      |
| `LambdaDataset`             | `LambdaDataSet`             | `kedro.io.lambda_dataset`      |
| `IncrementalDataset`        | `IncrementalDataSet`        | `kedro.io.partitioned_dataset` |
| `MemoryDataset`             | `MemoryDataSet`             | `kedro.io.memory_dataset`      |
| `PartitionedDataset`        | `PartitionedDataSet`        | `kedro.io.partitioned_dataset` |
| `DatasetError`              | `DataSetError`              | `kedro.io.core`                |
| `DatasetAlreadyExistsError` | `DataSetAlreadyExistsError` | `kedro.io.core`                |
| `DatasetNotFoundError`      | `DataSetNotFoundError`      | `kedro.io.core`                |

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:

* [jmalovera10](https://github.com/jmalovera10)
* [debugger24](https://github.com/debugger24)
* [juliushetzel](https://github.com/juliushetzel)
* [jacobweiss2305](https://github.com/jacobweiss2305)
* [eduardoconto](https://github.com/eduardoconto)

# Release 0.18.10

## Major features and improvements
* Rebrand across all documentation and Kedro assets.
* Added support for variable interpolation in the catalog with the `OmegaConfigLoader`.

# Release 0.18.9

## Major features and improvements
* `kedro run --params` now updates interpolated parameters correctly when using `OmegaConfigLoader`.
* Added `metadata` attribute to `kedro.io` datasets. This is ignored by Kedro, but may be consumed by users or external plugins.
* Added `kedro.logging.RichHandler`. This replaces the default `rich.logging.RichHandler` and is more flexible, user can turn off the `rich` traceback if needed.

## Bug fixes and other changes
* `OmegaConfigLoader` will return a `dict` instead of `DictConfig`.
* `OmegaConfigLoader` does not show a `MissingConfigError` when the config files exist but are empty.

## Documentation changes
* Added documentation for collaborative experiment tracking within Kedro-Viz.
* Revised section on deployment to better organise content and reflect how recently docs have been updated.
* Minor improvements to fix typos and revise docs to align with engineering changes.

## Breaking changes to the API
* `kedro package` does not produce `.egg` files anymore, and now relies exclusively on `.whl` files.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:

* [tomasvanpottelbergh](https://github.com/tomasvanpottelbergh)
* [https://github.com/debugger24](https://github.com/debugger24)

# Release 0.18.8

## Major features and improvements
* Added `KEDRO_LOGGING_CONFIG` environment variable, which can be used to configure logging from the beginning of the `kedro` process.
* Removed logs folder from the kedro new project template. File-based logging will remain but just be level INFO and above and go to project root instead.


## Bug fixes and other changes
* Improvements to Jupyter E2E tests.
* Added full `kedro run` CLI command to session store to improve run reproducibility using `Kedro-Viz` experiment tracking.

### Documentation changes
* Improvements to documentation about configuration.
* Improvements to Sphinx toolchain including incrementing to use a newer version.
* Improvements to documentation on visualising Kedro projects on Databricks, and additional documentation about the development workflow for Kedro projects on Databricks.
* Updated Technical Steering Committee membership documentation.
* Revised documentation section about linting and formatting and extended to give details of `flake8` configuration.
* Updated table of contents for documentation to reduce scrolling.
* Expanded FAQ documentation.
* Added a 404 page to documentation.
* Added deprecation warnings about the removal of `kedro.extras.datasets`.

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:

* [MaximeSteinmetz](https://github.com/MaximeSteinmetz)


# Release 0.18.7

## Major features and improvements
* Added new Kedro CLI `kedro jupyter setup` to setup Jupyter Kernel for Kedro.
* `kedro package` now includes the project configuration in a compressed `tar.gz` file.
* Added functionality to the `OmegaConfigLoader` to load configuration from compressed files of `zip` or `tar` format. This feature requires `fsspec>=2023.1.0`.
* Significant improvements to on-boarding documentation that covers setup for new Kedro users. Also some major changes to the spaceflights tutorial to make it faster to work through. We think it's a better read. Tell us if it's not.

## Bug fixes and other changes
* Added a guide and tooling for developing Kedro for Databricks.
* Implemented missing dict-like interface for `_ProjectPipeline`.


# Release 0.18.6

## Bug fixes and other changes
* Fixed bug that didn't allow to read or write datasets with `s3a` or `s3n` filepaths
* Fixed bug with overriding nested parameters using the `--params` flag
* Fixed bug that made session store incompatible with `Kedro-Viz` experiment tracking

## Migration guide from Kedro 0.18.5 to 0.18.6
A regression introduced in Kedro version `0.18.5` caused the `Kedro-Viz` console to fail to show experiment tracking correctly. If you experienced this issue, you will need to:
* upgrade to Kedro version `0.18.6`
* delete any erroneous session entries created with Kedro 0.18.5 from your session_store.db stored at `<project-path>/data/session_store.db`.

Thanks to Kedroids tomohiko kato, [tsanikgr](https://github.com/tsanikgr) and [maddataanalyst](https://github.com/maddataanalyst) for very detailed reports about the bug.


# Release 0.18.5

> This release introduced a bug that causes a failure in experiment tracking within the `Kedro-Viz` console. We recommend that you use Kedro version `0.18.6` in preference.

## Major features and improvements
* Added new `OmegaConfigLoader` which uses `OmegaConf` for loading and merging configuration.
* Added the `--conf-source` option to `kedro run`, allowing users to specify a source for project configuration for the run.
* Added `omegaconf` syntax as option for `--params`. Keys and values can now be separated by colons or equals signs.
* Added support for generator functions as nodes, i.e. using `yield` instead of return.
  * Enable chunk-wise processing in nodes with generator functions.
  * Save node outputs after every `yield` before proceeding with next chunk.
* Fixed incorrect parsing of Azure Data Lake Storage Gen2 URIs used in datasets.
* Added support for loading credentials from environment variables using `OmegaConfigLoader`.
* Added new `--namespace` flag to `kedro run` to enable filtering by node namespace.
* Added a new argument `node` for all four dataset hooks.
* Added the `kedro run` flags `--nodes`, `--tags`, and `--load-versions` to replace `--node`, `--tag`, and `--load-version`.

## Bug fixes and other changes
* Commas surrounded by square brackets (only possible for nodes with default names) will no longer split the arguments to `kedro run` options which take a list of nodes as inputs (`--from-nodes` and `--to-nodes`).
* Fixed bug where `micropkg` manifest section in `pyproject.toml` isn't recognised as allowed configuration.
* Fixed bug causing `load_ipython_extension` not to register the `%reload_kedro` line magic when called in a directory that does not contain a Kedro project.
* Added `anyconfig`'s `ac_context` parameter to `kedro.config.commons` module functions for more flexible `ConfigLoader` customizations.
* Change reference to `kedro.pipeline.Pipeline` object throughout test suite with `kedro.modular_pipeline.pipeline` factory.
* Fixed bug causing the `after_dataset_saved` hook only to be called for one output dataset when multiple are saved in a single node and async saving is in use.
* Log level for "Credentials not found in your Kedro project config" was changed from `WARNING` to `DEBUG`.
* Added safe extraction of tar files in `micropkg pull` to fix vulnerability caused by [CVE-2007-4559](https://github.com/advisories/GHSA-gw9q-c7gh-j9vm).
* Documentation improvements
    * Bug fix in table font size
    * Updated API docs links for datasets
    * Improved CLI docs for `kedro run`
    * Revised documentation for visualisation to build plots and for experiment tracking
    * Added example for loading external credentials to the Hooks documentation

## Breaking changes to the API

## Community contributions
Many thanks to the following Kedroids for contributing PRs to this release:

* [adamfrly](https://github.com/adamfrly)
* [corymaklin](https://github.com/corymaklin)
* [Emiliopb](https://github.com/Emiliopb)
* [grhaonan](https://github.com/grhaonan)
* [JStumpp](https://github.com/JStumpp)
* [michalbrys](https://github.com/michalbrys)
* [sbrugman](https://github.com/sbrugman)

## Upcoming deprecations for Kedro 0.19.0
* `project_version` will be deprecated in `pyproject.toml` please use `kedro_init_version` instead.
* Deprecated `kedro run` flags `--node`, `--tag`, and `--load-version` in favour of `--nodes`, `--tags`, and `--load-versions`.

# Release 0.18.4

## Major features and improvements
* Make Kedro instantiate datasets from `kedro_datasets` with higher priority than `kedro.extras.datasets`. `kedro_datasets` is the namespace for the new `kedro-datasets` python package.
* The config loader objects now implement `UserDict` and the configuration is accessed through `conf_loader['catalog']`.
* You can configure config file patterns through `settings.py` without creating a custom config loader.
* Added the following new datasets:

| Type                                 | Description                                                                | Location                         |
| ------------------------------------ | -------------------------------------------------------------------------- | -------------------------------- |
| `svmlight.SVMLightDataSet`           | Work with svmlight/libsvm files using scikit-learn library                 | `kedro.extras.datasets.svmlight` |
| `video.VideoDataSet`                 | Read and write video files from a filesystem                               | `kedro.extras.datasets.video`    |
| `video.video_dataset.SequenceVideo`  | Create a video object from an iterable sequence to use with `VideoDataSet` | `kedro.extras.datasets.video`    |
| `video.video_dataset.GeneratorVideo` | Create a video object from a generator to use with `VideoDataSet`          | `kedro.extras.datasets.video`    |
* Implemented support for a functional definition of schema in `dask.ParquetDataSet` to work with the `dask.to_parquet` API.

## Bug fixes and other changes
* Fixed `kedro micropkg pull` for packages on PyPI.
* Fixed `format` in `save_args` for `SparkHiveDataSet`, previously it didn't allow you to save it as delta format.
* Fixed save errors in `TensorFlowModelDataset` when used without versioning; previously, it wouldn't overwrite an existing model.
* Added support for `tf.device` in `TensorFlowModelDataset`.
* Updated error message for `VersionNotFoundError` to handle insufficient permission issues for cloud storage.
* Updated Experiment Tracking docs with working examples.
* Updated `MatplotlibWriter`, `text.TextDataSet`, `plotly.PlotlyDataSet` and `plotly.JSONDataSet` docs with working examples.
* Modified implementation of the Kedro IPython extension to use `local_ns` rather than a global variable.
* Refactored `ShelveStore` to its own module to ensure multiprocessing works with it.
* `kedro.extras.datasets.pandas.SQLQueryDataSet` now takes optional argument `execution_options`.
* Removed `attrs` upper bound to support newer versions of Airflow.
* Bumped the lower bound for the `setuptools` dependency to <=61.5.1.

## Minor breaking changes to the API

## Upcoming deprecations for Kedro 0.19.0
* `kedro test` and `kedro lint` will be deprecated.

## Documentation
* Revised the Introduction to shorten it
* Revised the Get Started section to remove unnecessary information and clarify the learning path
* Updated the spaceflights tutorial to simplify the later stages and clarify what the reader needed to do in each phase
* Moved some pages that covered advanced materials into more appropriate sections
* Moved visualisation into its own section
* Fixed a bug that degraded user experience: the table of contents is now sticky when you navigate between pages
* Added redirects where needed on ReadTheDocs for legacy links and bookmarks

## Contributions from the Kedroid community
We are grateful to the following for submitting PRs that contributed to this release: [jstammers](https://github.com/jstammers), [FlorianGD](https://github.com/FlorianGD), [yash6318](https://github.com/yash6318), [carlaprv](https://github.com/carlaprv), [dinotuku](https://github.com/dinotuku), [williamcaicedo](https://github.com/williamcaicedo), [avan-sh](https://github.com/avan-sh), [Kastakin](https://github.com/Kastakin), [amaralbf](https://github.com/amaralbf), [BSGalvan](https://github.com/BSGalvan), [levimjoseph](https://github.com/levimjoseph), [daniel-falk](https://github.com/daniel-falk), [clotildeguinard](https://github.com/clotildeguinard), [avsolatorio](https://github.com/avsolatorio), and [picklejuicedev](https://github.com/picklejuicedev) for comments and input to documentation changes

# Release 0.18.3

## Major features and improvements
* Implemented autodiscovery of project pipelines. A pipeline created with `kedro pipeline create <pipeline_name>` can now be accessed immediately without needing to explicitly register it in `src/<package_name>/pipeline_registry.py`, either individually by name (e.g. `kedro run --pipeline=<pipeline_name>`) or as part of the combined default pipeline (e.g. `kedro run`). By default, the simplified `register_pipelines()` function in `pipeline_registry.py` looks like:

    ```python
    def register_pipelines() -> Dict[str, Pipeline]:
        """Register the project's pipelines.

        Returns:
            A mapping from pipeline names to ``Pipeline`` objects.
        """
        pipelines = find_pipelines()
        pipelines["__default__"] = sum(pipelines.values())
        return pipelines
    ```

* The Kedro IPython extension should now be loaded with `%load_ext kedro.ipython`.
* The line magic `%reload_kedro` now accepts keywords arguments, e.g. `%reload_kedro --env=prod`.
* Improved resume pipeline suggestion for `SequentialRunner`, it will backtrack the closest persisted inputs to resume.

## Bug fixes and other changes

* Changed default `False` value for rich logging `show_locals`, to make sure credentials and other sensitive data isn't shown in logs.
* Rich traceback handling is disabled on Databricks so that exceptions now halt execution as expected. This is a workaround for a [bug in `rich`](https://github.com/Textualize/rich/issues/2455).
* When using `kedro run -n [some_node]`, if `some_node` is missing a namespace the resulting error message will suggest the correct node name.
* Updated documentation for `rich` logging.
* Updated Prefect deployment documentation to allow for reruns with saved versioned datasets.
* The Kedro IPython extension now surfaces errors when it cannot load a Kedro project.
* Relaxed `delta-spark` upper bound to allow compatibility with Spark 3.1.x and 3.2.x.
* Added `gdrive` to list of cloud protocols, enabling Google Drive paths for datasets.
* Added svg logo resource for ipython kernel.

## Upcoming deprecations for Kedro 0.19.0
* The Kedro IPython extension will no longer be available as `%load_ext kedro.extras.extensions.ipython`; use `%load_ext kedro.ipython` instead.
* `kedro jupyter convert`, `kedro build-docs`, `kedro build-reqs` and `kedro activate-nbstripout` will be deprecated.

# Release 0.18.2

## Major features and improvements
* Added `abfss` to list of cloud protocols, enabling abfss paths.
* Kedro now uses the [Rich](https://github.com/Textualize/rich) library to format terminal logs and tracebacks.
* The file `conf/base/logging.yml` is now optional. See [our documentation](https://docs.kedro.org/en/0.18.2/logging/logging.html) for details.
* Introduced a `kedro.starters` entry point. This enables plugins to create custom starter aliases used by `kedro starter list` and `kedro new`.
* Reduced the `kedro new` prompts to just one question asking for the project name.

## Bug fixes and other changes
* Bumped `pyyaml` upper bound to make Kedro compatible with the [pyodide](https://pyodide.org/en/stable/usage/loading-packages.html#micropip) stack.
* Updated project template's Sphinx configuration to use `myst_parser` instead of `recommonmark`.
* Reduced number of log lines by changing the logging level from `INFO` to `DEBUG` for low priority messages.
* Kedro's framework-side logging configuration no longer performs file-based logging. Hence superfluous `info.log`/`errors.log` files are no longer created in your project root, and running Kedro on read-only file systems such as Databricks Repos is now possible.
* The `root` logger is now set to the Python default level of `WARNING` rather than `INFO`. Kedro's logger is still set to emit `INFO` level messages.
* `SequentialRunner` now has consistent execution order across multiple runs with sorted nodes.
* Bumped the upper bound for the Flake8 dependency to <5.0.
* `kedro jupyter notebook/lab` no longer reuses a Jupyter kernel.
* Required `cookiecutter>=2.1.1` to address a [known command injection vulnerability](https://security.snyk.io/vuln/SNYK-PYTHON-COOKIECUTTER-2414281).
* The session store no longer fails if a username cannot be found with `getpass.getuser`.
* Added generic typing for `AbstractDataSet` and `AbstractVersionedDataSet` as well as typing to all datasets.
* Rendered the deployment guide flowchart as a Mermaid diagram, and added Dask.

## Minor breaking changes to the API
* The module `kedro.config.default_logger` no longer exists; default logging configuration is now set automatically through `kedro.framework.project.LOGGING`. Unless you explicitly import `kedro.config.default_logger` you do not need to make any changes.

## Upcoming deprecations for Kedro 0.19.0
* `kedro.extras.ColorHandler` will be removed in 0.19.0.

# Release 0.18.1

## Major features and improvements
* Added a new hook `after_context_created` that passes the `KedroContext` instance as `context`.
* Added a new CLI hook `after_command_run`.
* Added more detail to YAML `ParserError` exception error message.
* Added option to `SparkDataSet` to specify a `schema` load argument that allows for supplying a user-defined schema as opposed to relying on the schema inference of Spark.
* The Kedro package no longer contains a built version of the Kedro documentation significantly reducing the package size.

## Bug fixes and other changes
* Removed fatal error from being logged when a Kedro session is created in a directory without git.
* `KedroContext` is now a attr's dataclass, `config_loader` is available as public attribute.
* Fixed `CONFIG_LOADER_CLASS` validation so that `TemplatedConfigLoader` can be specified in settings.py. Any `CONFIG_LOADER_CLASS` must be a subclass of `AbstractConfigLoader`.
* Added runner name to the `run_params` dictionary used in pipeline hooks.
* Updated [Databricks documentation](https://docs.kedro.org/en/0.18.1/deployment/databricks.html) to include how to get it working with IPython extension and Kedro-Viz.
* Update sections on visualisation, namespacing, and experiment tracking in the spaceflight tutorial to correspond to the complete spaceflights starter.
* Fixed `Jinja2` syntax loading with `TemplatedConfigLoader` using `globals.yml`.
* Removed global `_active_session`, `_activate_session` and `_deactivate_session`. Plugins that need to access objects such as the config loader should now do so through `context` in the new `after_context_created` hook.
* `config_loader` is available as a public read-only attribute of `KedroContext`.
* Made `hook_manager` argument optional for `runner.run`.
* `kedro docs` now opens an online version of the Kedro documentation instead of a locally built version.

## Upcoming deprecations for Kedro 0.19.0
* `kedro docs` will be removed in 0.19.0.


# Release 0.18.0

## TL;DR ✨
Kedro 0.18.0 strives to reduce the complexity of the project template and get us closer to a stable release of the framework. We've introduced the full [micro-packaging workflow](https://docs.kedro.org/en/0.18.0/nodes_and_pipelines/micro_packaging.html) 📦, which allows you to import packages, utility functions and existing pipelines into your Kedro project. [Integration with IPython and Jupyter](https://docs.kedro.org/en/0.18.0/tools_integration/ipython.html) has been streamlined in preparation for enhancements to Kedro's interactive workflow. Additionally, the release comes with long-awaited Python 3.9 and 3.10 support 🐍.

## Major features and improvements

### Framework
* Added `kedro.config.abstract_config.AbstractConfigLoader` as an abstract base class for all `ConfigLoader` implementations. `ConfigLoader` and `TemplatedConfigLoader` now inherit directly from this base class.
* Streamlined the `ConfigLoader.get` and `TemplatedConfigLoader.get` API and delegated the actual `get` method functional implementation to the `kedro.config.common` module.
* The `hook_manager` is no longer a global singleton. The `hook_manager` lifecycle is now managed by the `KedroSession`, and a new `hook_manager` will be created every time a `session` is instantiated.
* Added support for specifying parameters mapping in `pipeline()` without the `params:` prefix.
* Added new API `Pipeline.filter()` (previously in `KedroContext._filter_pipeline()`) to filter parts of a pipeline.
* Added `username` to Session store for logging during Experiment Tracking.
* A packaged Kedro project can now be imported and run from another Python project as following:
```python
from my_package.__main__ import main

main(
    ["--pipleine", "my_pipeline"]
)  # or just main() if no parameters are needed for the run
```

### Project template
* Removed `cli.py` from the Kedro project template. By default, all CLI commands, including `kedro run`, are now defined on the Kedro framework side. You can still define custom CLI commands by creating your own `cli.py`.
* Removed `hooks.py` from the Kedro project template. Registration hooks have been removed in favour of `settings.py` configuration, but you can still define execution timeline hooks by creating your own `hooks.py`.
* Removed `.ipython` directory from the Kedro project template. The IPython/Jupyter workflow no longer uses IPython profiles; it now uses an IPython extension.
* The default `kedro` run configuration environment names can now be set in `settings.py` using the `CONFIG_LOADER_ARGS` variable. The relevant keyword arguments to supply are `base_env` and `default_run_env`, which are set to `base` and `local` respectively by default.

### DataSets
* Added the following new datasets:

| Type                      | Description                                                   | Location                         |
| ------------------------- | ------------------------------------------------------------- | -------------------------------- |
| `pandas.XMLDataSet`       | Read XML into Pandas DataFrame. Write Pandas DataFrame to XML | `kedro.extras.datasets.pandas`   |
| `networkx.GraphMLDataSet` | Work with NetworkX using GraphML files                        | `kedro.extras.datasets.networkx` |
| `networkx.GMLDataSet`     | Work with NetworkX using Graph Modelling Language files       | `kedro.extras.datasets.networkx` |
| `redis.PickleDataSet`     | loads/saves data from/to a Redis database                     | `kedro.extras.datasets.redis`    |

* Added `partitionBy` support and exposed `save_args` for `SparkHiveDataSet`.
* Exposed `open_args_save` in `fs_args` for `pandas.ParquetDataSet`.
* Refactored the `load` and `save` operations for `pandas` datasets in order to leverage `pandas` own API and delegate `fsspec` operations to them. This reduces the need to have our own `fsspec` wrappers.
* Merged `pandas.AppendableExcelDataSet` into `pandas.ExcelDataSet`.
* Added `save_args` to `feather.FeatherDataSet`.

### Jupyter and IPython integration
* The [only recommended way to work with Kedro in Jupyter or IPython is now the Kedro IPython extension](https://docs.kedro.org/en/0.18.0/tools_integration/ipython.html). Managed Jupyter instances should load this via `%load_ext kedro.ipython` and use the line magic `%reload_kedro`.
* `kedro ipython` launches an IPython session that preloads the Kedro IPython extension.
* `kedro jupyter notebook/lab` creates a custom Jupyter kernel that preloads the Kedro IPython extension and launches a notebook with that kernel selected. There is no longer a need to specify `--all-kernels` to show all available kernels.

### Dependencies
* Bumped the minimum version of `pandas` to 1.3. Any `storage_options` should continue to be specified under `fs_args` and/or `credentials`.
* Added support for Python 3.9 and 3.10, dropped support for Python 3.6.
* Updated `black` dependency in the project template to a non pre-release version.

### Other
* Documented distribution of Kedro pipelines with Dask.

## Breaking changes to the API

### Framework
* Removed `RegistrationSpecs` and its associated `register_config_loader` and `register_catalog` hook specifications in favour of `CONFIG_LOADER_CLASS`/`CONFIG_LOADER_ARGS` and `DATA_CATALOG_CLASS` in `settings.py`.
* Removed deprecated functions `load_context` and `get_project_context`.
* Removed deprecated `CONF_SOURCE`, `package_name`, `pipeline`, `pipelines`, `config_loader` and `io` attributes from `KedroContext` as well as the deprecated `KedroContext.run` method.
* Added the `PluginManager` `hook_manager` argument to `KedroContext` and the `Runner.run()` method, which will be provided by the `KedroSession`.
* Removed the public method `get_hook_manager()` and replaced its functionality by `_create_hook_manager()`.
* Enforced that only one run can be successfully executed as part of a `KedroSession`. `run_id` has been renamed to `session_id` as a result.

### Configuration loaders
* The `settings.py` setting `CONF_ROOT` has been renamed to `CONF_SOURCE`. Default value of `conf` remains unchanged.
* `ConfigLoader` and `TemplatedConfigLoader` argument `conf_root` has been renamed to `conf_source`.
* `extra_params` has been renamed to `runtime_params` in `kedro.config.config.ConfigLoader` and `kedro.config.templated_config.TemplatedConfigLoader`.
* The environment defaulting behaviour has been removed from `KedroContext` and is now implemented in a `ConfigLoader` class (or equivalent) with the `base_env` and `default_run_env` attributes.

### DataSets
* `pandas.ExcelDataSet` now uses `openpyxl` engine instead of `xlrd`.
* `pandas.ParquetDataSet` now calls `pd.to_parquet()` upon saving. Note that the argument `partition_cols` is not supported.
* `spark.SparkHiveDataSet` API has been updated to reflect `spark.SparkDataSet`. The `write_mode=insert` option has also been replaced with `write_mode=append` as per Spark styleguide. This change addresses [Issue 725](https://github.com/kedro-org/kedro/issues/725) and [Issue 745](https://github.com/kedro-org/kedro/issues/745). Additionally, `upsert` mode now leverages `checkpoint` functionality and requires a valid `checkpointDir` be set for current `SparkContext`.
* `yaml.YAMLDataSet` can no longer save a `pandas.DataFrame` directly, but it can save a dictionary. Use `pandas.DataFrame.to_dict()` to convert your `pandas.DataFrame` to a dictionary before you attempt to save it to YAML.
* Removed `open_args_load` and `open_args_save` from the following datasets:
  * `pandas.CSVDataSet`
  * `pandas.ExcelDataSet`
  * `pandas.FeatherDataSet`
  * `pandas.JSONDataSet`
  * `pandas.ParquetDataSet`
* `storage_options` are now dropped if they are specified under `load_args` or `save_args` for the following datasets:
  * `pandas.CSVDataSet`
  * `pandas.ExcelDataSet`
  * `pandas.FeatherDataSet`
  * `pandas.JSONDataSet`
  * `pandas.ParquetDataSet`
* Renamed `lambda_data_set`, `memory_data_set`, and `partitioned_data_set` to `lambda_dataset`, `memory_dataset`, and `partitioned_dataset`, respectively, in `kedro.io`.
* The dataset `networkx.NetworkXDataSet` has been renamed to `networkx.JSONDataSet`.

### CLI
* Removed `kedro install` in favour of `pip install -r src/requirements.txt` to install project dependencies.
* Removed `--parallel` flag from `kedro run` in favour of `--runner=ParallelRunner`. The `-p` flag is now an alias for `--pipeline`.
* `kedro pipeline package` has been replaced by `kedro micropkg package` and, in addition to the `--alias` flag used to rename the package, now accepts a module name and path to the pipeline or utility module to package, relative to `src/<package_name>/`. The `--version` CLI option has been removed in favour of setting a `__version__` variable in the micro-package's `__init__.py` file.
* `kedro pipeline pull` has been replaced by `kedro micropkg pull` and now also supports `--destination` to provide a location for pulling the package.
* Removed `kedro pipeline list` and `kedro pipeline describe` in favour of `kedro registry list` and `kedro registry describe`.
* `kedro package` and `kedro micropkg package` now save `egg` and `whl` or `tar` files in the `<project_root>/dist` folder (previously `<project_root>/src/dist`).
* Changed the behaviour of `kedro build-reqs` to compile requirements from `requirements.txt` instead of `requirements.in` and save them to `requirements.lock` instead of `requirements.txt`.
* `kedro jupyter notebook/lab` no longer accept `--all-kernels` or `--idle-timeout` flags. `--all-kernels` is now the default behaviour.
* `KedroSession.run` now raises `ValueError` rather than `KedroContextError` when the pipeline contains no nodes. The same `ValueError` is raised when there are no matching tags.
* `KedroSession.run` now raises `ValueError` rather than `KedroContextError` when the pipeline name doesn't exist in the pipeline registry.

### Other
* Added namespace to parameters in a modular pipeline, which addresses [Issue 399](https://github.com/kedro-org/kedro/issues/399).
* Switched from packaging pipelines as wheel files to tar archive files compressed with gzip (`.tar.gz`).
* Removed decorator API from `Node` and `Pipeline`, as well as the modules `kedro.extras.decorators` and `kedro.pipeline.decorators`.
* Removed transformer API from `DataCatalog`, as well as the modules `kedro.extras.transformers` and `kedro.io.transformers`.
* Removed the `Journal` and `DataCatalogWithDefault`.
* Removed `%init_kedro` IPython line magic, with its functionality incorporated into `%reload_kedro`. This means that if `%reload_kedro` is called with a filepath, that will be set as default for subsequent calls.

## Migration guide from Kedro 0.17.* to 0.18.*

### Hooks
* Remove any existing `hook_impl` of the `register_config_loader` and `register_catalog` methods from `ProjectHooks` in `hooks.py` (or custom alternatives).
* If you use `run_id` in the `after_catalog_created` hook, replace it with `save_version` instead.
* If you use `run_id` in any of the `before_node_run`, `after_node_run`, `on_node_error`, `before_pipeline_run`, `after_pipeline_run` or `on_pipeline_error` hooks, replace it with `session_id` instead.

### `settings.py` file
* If you use a custom config loader class such as `kedro.config.TemplatedConfigLoader`, alter `CONFIG_LOADER_CLASS` to specify the class and `CONFIG_LOADER_ARGS` to specify keyword arguments. If not set, these default to `kedro.config.ConfigLoader` and an empty dictionary respectively.
* If you use a custom data catalog class, alter `DATA_CATALOG_CLASS` to specify the class. If not set, this defaults to `kedro.io.DataCatalog`.
* If you have a custom config location (i.e. not `conf`), update `CONF_ROOT` to `CONF_SOURCE` and set it to a string with the expected configuration location. If not set, this defaults to `"conf"`.

### Modular pipelines
* If you use any modular pipelines with parameters, make sure they are declared with the correct namespace. See example below:

For a given pipeline:
```python
active_pipeline = pipeline(
    pipe=[
        node(
            func=some_func,
            inputs=["model_input_table", "params:model_options"],
            outputs=["**my_output"],
        ),
        ...,
    ],
    inputs="model_input_table",
    namespace="candidate_modelling_pipeline",
)
```

The parameters should look like this:

```diff
-model_options:
-    test_size: 0.2
-    random_state: 8
-    features:
-    - engines
-    - passenger_capacity
-    - crew
+candidate_modelling_pipeline:
+    model_options:
+      test_size: 0.2
+      random_state: 8
+      features:
+        - engines
+        - passenger_capacity
+        - crew

```
* Optional: You can now remove all `params:` prefix when supplying values to `parameters` argument in a `pipeline()` call.
* If you pull modular pipelines with `kedro pipeline pull my_pipeline --alias other_pipeline`, now use `kedro micropkg pull my_pipeline --alias pipelines.other_pipeline` instead.
* If you package modular pipelines with `kedro pipeline package my_pipeline`, now use `kedro micropkg package pipelines.my_pipeline` instead.
* Similarly, if you package any modular pipelines using `pyproject.toml`, you should modify the keys to include the full module path, and wrapped in double-quotes, e.g:

```diff
[tool.kedro.micropkg.package]
-data_engineering = {destination = "path/to/here"}
-data_science = {alias = "ds", env = "local"}
+"pipelines.data_engineering" = {destination = "path/to/here"}
+"pipelines.data_science" = {alias = "ds", env = "local"}

[tool.kedro.micropkg.pull]
-"s3://my_bucket/my_pipeline" = {alias = "aliased_pipeline"}
+"s3://my_bucket/my_pipeline" = {alias = "pipelines.aliased_pipeline"}
```

### DataSets
* If you use `pandas.ExcelDataSet`, make sure you have `openpyxl` installed in your environment. This is automatically installed if you specify `kedro[pandas.ExcelDataSet]==0.18.0` in your `requirements.txt`. You can uninstall `xlrd` if you were only using it for this dataset.
* If you use`pandas.ParquetDataSet`, pass pandas saving arguments directly to `save_args` instead of nested in `from_pandas` (e.g. `save_args = {"preserve_index": False}` instead of `save_args = {"from_pandas": {"preserve_index": False}}`).
* If you use `spark.SparkHiveDataSet` with `write_mode` option set to `insert`, change this to `append` in line with the Spark styleguide. If you use `spark.SparkHiveDataSet` with `write_mode` option set to `upsert`, make sure that your `SparkContext` has a valid `checkpointDir` set either by `SparkContext.setCheckpointDir` method or directly in the `conf` folder.
* If you use `pandas~=1.2.0` and pass `storage_options` through `load_args` or `savs_args`, specify them under `fs_args` or via `credentials` instead.
* If you import from `kedro.io.lambda_data_set`, `kedro.io.memory_data_set`, or `kedro.io.partitioned_data_set`, change the import to `kedro.io.lambda_dataset`, `kedro.io.memory_dataset`, or `kedro.io.partitioned_dataset`, respectively (or import the dataset directly from `kedro.io`).
* If you have any `pandas.AppendableExcelDataSet` entries in your catalog, replace them with `pandas.ExcelDataSet`.
* If you have any `networkx.NetworkXDataSet` entries in your catalog, replace them with `networkx.JSONDataSet`.

### Other
* Edit any scripts containing `kedro pipeline package --version` to use `kedro micropkg package` instead. If you wish to set a specific pipeline package version, set the `__version__` variable in the pipeline package's `__init__.py` file.
* To run a pipeline in parallel, use `kedro run --runner=ParallelRunner` rather than `--parallel` or `-p`.
* If you call `ConfigLoader` or `TemplatedConfigLoader` directly, update the keyword arguments `conf_root` to `conf_source` and `extra_params` to `runtime_params`.
* If you use `KedroContext` to access `ConfigLoader`, use `settings.CONFIG_LOADER_CLASS` to access the currently used `ConfigLoader` instead.
* The signature of `KedroContext` has changed and now needs `config_loader` and `hook_manager` as additional arguments of type `ConfigLoader` and `PluginManager` respectively.

# Release 0.17.7

## Major features and improvements
* `pipeline` now accepts `tags` and a collection of `Node`s and/or `Pipeline`s rather than just a single `Pipeline` object. `pipeline` should be used in preference to `Pipeline` when creating a Kedro pipeline.
* `pandas.SQLTableDataSet` and `pandas.SQLQueryDataSet` now only open one connection per database, at instantiation time (therefore at catalog creation time), rather than one per load/save operation.
* Added new command group, `micropkg`, to replace `kedro pipeline pull` and `kedro pipeline package` with `kedro micropkg pull` and `kedro micropkg package` for Kedro 0.18.0. `kedro micropkg package` saves packages to `project/dist` while `kedro pipeline package` saves packages to `project/src/dist`.

## Bug fixes and other changes
* Added tutorial documentation for [experiment tracking](https://docs.kedro.org/en/0.17.7/08_logging/02_experiment_tracking.html).
* Added [Plotly dataset documentation](https://docs.kedro.org/en/0.17.7/03_tutorial/05_visualise_pipeline.html#visualise-plotly-charts-in-kedro-viz).
* Added the upper limit `pandas<1.4` to maintain compatibility with `xlrd~=1.0`.
* Bumped the `Pillow` minimum version requirement to 9.0 (Python 3.7+ only) following [CVE-2022-22817](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-22817).
* Fixed `PickleDataSet` to be copyable and hence work with the parallel runner.
* Upgraded `pip-tools`, which is used by `kedro build-reqs`, to 6.5 (Python 3.7+ only). This `pip-tools` version is compatible with `pip>=21.2`, including the most recent releases of `pip`. Python 3.6 users should continue to use `pip-tools` 6.4 and `pip<22`.
* Added `astro-iris` as alias for `astro-airlow-iris`, so that old tutorials can still be followed.
* Added details about [Kedro's Technical Steering Committee and governance model](https://docs.kedro.org/en/0.17.7/14_contribution/technical_steering_committee.html).

## Upcoming deprecations for Kedro 0.18.0
* `kedro pipeline pull` and `kedro pipeline package` will be deprecated. Please use `kedro micropkg` instead.


# Release 0.17.6

## Major features and improvements
* Added `pipelines` global variable to IPython extension, allowing you to access the project's pipelines in `kedro ipython` or `kedro jupyter notebook`.
* Enabled overriding nested parameters with `params` in CLI, i.e. `kedro run --params="model.model_tuning.booster:gbtree"` updates parameters to `{"model": {"model_tuning": {"booster": "gbtree"}}}`.
* Added option to `pandas.SQLQueryDataSet` to specify a `filepath` with a SQL query, in addition to the current method of supplying the query itself in the `sql` argument.
* Extended `ExcelDataSet` to support saving Excel files with multiple sheets.
* Added the following new datasets:

| Type                      | Description                                                                                                            | Location                       |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `plotly.JSONDataSet`      | Works with plotly graph object Figures (saves as json file)                                                            | `kedro.extras.datasets.plotly` |
| `pandas.GenericDataSet`   | Provides a 'best effort' facility to read / write any format provided by the `pandas` library                          | `kedro.extras.datasets.pandas` |
| `pandas.GBQQueryDataSet`  | Loads data from a Google Bigquery table using provided SQL query                                                       | `kedro.extras.datasets.pandas` |
| `spark.DeltaTableDataSet` | Dataset designed to handle Delta Lake Tables and their CRUD-style operations, including `update`, `merge` and `delete` | `kedro.extras.datasets.spark`  |

## Bug fixes and other changes
* Fixed an issue where `kedro new --config config.yml` was ignoring the config file when `prompts.yml` didn't exist.
* Added documentation for `kedro viz --autoreload`.
* Added support for arbitrary backends (via importable module paths) that satisfy the `pickle` interface to `PickleDataSet`.
* Added support for `sum` syntax for connecting pipeline objects.
* Upgraded `pip-tools`, which is used by `kedro build-reqs`, to 6.4. This `pip-tools` version requires `pip>=21.2` while [adding support for `pip>=21.3`](https://github.com/jazzband/pip-tools/pull/1501). To upgrade `pip`, please refer to [their documentation](https://pip.pypa.io/en/stable/installing/#upgrading-pip).
* Relaxed the bounds on the `plotly` requirement for `plotly.PlotlyDataSet` and the `pyarrow` requirement for `pandas.ParquetDataSet`.
* `kedro pipeline package <pipeline>` now raises an error if the `<pipeline>` argument doesn't look like a valid Python module path (e.g. has `/` instead of `.`).
* Added new `overwrite` argument to `PartitionedDataSet` and `MatplotlibWriter` to enable deletion of existing partitions and plots on dataset `save`.
* `kedro pipeline pull` now works when the project requirements contains entries such as `-r`, `--extra-index-url` and local wheel files ([Issue #913](https://github.com/kedro-org/kedro/issues/913)).
* Fixed slow startup because of catalog processing by reducing the exponential growth of extra processing during `_FrozenDatasets` creations.
* Removed `.coveragerc` from the Kedro project template. `coverage` settings are now given in `pyproject.toml`.
* Fixed a bug where packaging or pulling a modular pipeline with the same name as the project's package name would throw an error (or silently pass without including the pipeline source code in the wheel file).
* Removed unintentional dependency on `git`.
* Fixed an issue where nested pipeline configuration was not included in the packaged pipeline.
* Deprecated the "Thanks for supporting contributions" section of release notes to simplify the contribution process; Kedro 0.17.6 is the last release that includes this. This process has been replaced with the [automatic GitHub feature](https://github.com/kedro-org/kedro/graphs/contributors).
* Fixed a bug where the version on the tracking datasets didn't match the session id and the versions of regular versioned datasets.
* Fixed an issue where datasets in `load_versions` that are not found in the data catalog would silently pass.
* Altered the string representation of nodes so that node inputs/outputs order is preserved rather than being alphabetically sorted.
* Update `APIDataSet` to accept `auth` through `credentials` and allow any iterable for `auth`.

## Upcoming deprecations for Kedro 0.18.0
* `kedro.extras.decorators` and `kedro.pipeline.decorators` are being deprecated in favour of Hooks.
* `kedro.extras.transformers` and `kedro.io.transformers` are being deprecated in favour of Hooks.
* The `--parallel` flag on `kedro run` is being removed in favour of `--runner=ParallelRunner`. The `-p` flag will change to be an alias for `--pipeline`.
* `kedro.io.DataCatalogWithDefault` is being deprecated, to be removed entirely in 0.18.0.

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman),
[Brites](https://github.com/brites101),
[Manish Swami](https://github.com/ManishS6),
[Avaneesh Yembadi](https://github.com/avan-sh),
[Zain Patel](https://github.com/mzjp2),
[Simon Brugman](https://github.com/sbrugman),
[Kiyo Kunii](https://github.com/921kiyo),
[Benjamin Levy](https://github.com/BenjaminLevyQB),
[Louis de Charsonville](https://github.com/louisdecharson),
[Simon Picard](https://github.com/simonpicard)

# Release 0.17.5

## Major features and improvements
* Added new CLI group `registry`, with the associated commands `kedro registry list` and `kedro registry describe`, to replace `kedro pipeline list` and `kedro pipeline describe`.
* Added support for dependency management at a modular pipeline level. When a pipeline with `requirements.txt` is packaged, its dependencies are embedded in the modular pipeline wheel file. Upon pulling the pipeline, Kedro will append dependencies to the project's `requirements.in`. More information is available in [our documentation](https://docs.kedro.org/en/0.17.5/06_nodes_and_pipelines/03_modular_pipelines.html).
* Added support for bulk packaging/pulling modular pipelines using `kedro pipeline package/pull --all` and `pyproject.toml`.
* Removed `cli.py` from the Kedro project template. By default all CLI commands, including `kedro run`, are now defined on the Kedro framework side. These can be overridden in turn by a plugin or a `cli.py` file in your project. A packaged Kedro project will respect the same hierarchy when executed with `python -m my_package`.
* Removed `.ipython/profile_default/startup/` from the Kedro project template in favour of `.ipython/profile_default/ipython_config.py` and the `kedro.extras.extensions.ipython`.
* Added support for `dill` backend to `PickleDataSet`.
* Imports are now refactored at `kedro pipeline package` and `kedro pipeline pull` time, so that _aliasing_ a modular pipeline doesn't break it.
* Added the following new datasets to support basic Experiment Tracking:

| Type                      | Description                                              | Location                         |
| ------------------------- | -------------------------------------------------------- | -------------------------------- |
| `tracking.MetricsDataSet` | Dataset to track numeric metrics for experiment tracking | `kedro.extras.datasets.tracking` |
| `tracking.JSONDataSet`    | Dataset to track data for experiment tracking            | `kedro.extras.datasets.tracking` |

## Bug fixes and other changes
* Bumped minimum required `fsspec` version to 2021.04.
* Fixed the `kedro install` and `kedro build-reqs` flows when uninstalled dependencies are present in a project's `settings.py`, `context.py` or `hooks.py` ([Issue #829](https://github.com/kedro-org/kedro/issues/829)).
* Imports are now refactored at `kedro pipeline package` and `kedro pipeline pull` time, so that _aliasing_ a modular pipeline doesn't break it.

## Minor breaking changes to the API
* Pinned `dynaconf` to `<3.1.6` because the method signature for `_validate_items` changed which is used in Kedro.

## Upcoming deprecations for Kedro 0.18.0
* `kedro pipeline list` and `kedro pipeline describe` are being deprecated in favour of new commands `kedro registry list ` and `kedro registry describe`.
* `kedro install` is being deprecated in favour of using `pip install -r src/requirements.txt` to install project dependencies.

## Thanks for supporting contributions
[Moussa Taifi](https://github.com/moutai),
[Deepyaman Datta](https://github.com/deepyaman)

# Release 0.17.4

## Major features and improvements
* Added the following new datasets:

| Type                   | Description                                                 | Location                       |
| ---------------------- | ----------------------------------------------------------- | ------------------------------ |
| `plotly.PlotlyDataSet` | Works with plotly graph object Figures (saves as json file) | `kedro.extras.datasets.plotly` |

## Bug fixes and other changes
* Defined our set of Kedro Principles! Have a read through [our docs](https://docs.kedro.org/en/0.17.4/12_faq/03_kedro_principles.html).
* `ConfigLoader.get()` now raises a `BadConfigException`, with a more helpful error message, if a configuration file cannot be loaded (for instance due to wrong syntax or poor formatting).
* `run_id` now defaults to `save_version` when `after_catalog_created` is called, similarly to what happens during a `kedro run`.
* Fixed a bug where `kedro ipython` and `kedro jupyter notebook` didn't work if the `PYTHONPATH` was already set.
* Update the IPython extension to allow passing `env` and `extra_params` to `reload_kedro`  similar to how the IPython script works.
* `kedro info` now outputs if a plugin has any `hooks` or `cli_hooks` implemented.
* `PartitionedDataSet` now supports lazily materializing data on save.
* `kedro pipeline describe` now defaults to the `__default__` pipeline when no pipeline name is provided and also shows the namespace the nodes belong to.
* Fixed an issue where spark.SparkDataSet with enabled versioning would throw a VersionNotFoundError when using databricks-connect from a remote machine and saving to dbfs filesystem.
* `EmailMessageDataSet` added to doctree.
* When node inputs do not pass validation, the error message is now shown as the most recent exception in the traceback ([Issue #761](https://github.com/kedro-org/kedro/issues/761)).
* `kedro pipeline package` now only packages the parameter file that exactly matches the pipeline name specified and the parameter files in a directory with the pipeline name.
* Extended support to newer versions of third-party dependencies ([Issue #735](https://github.com/kedro-org/kedro/issues/735)).
* Ensured consistent references to `model input` tables in accordance with our Data Engineering convention.
* Changed behaviour where `kedro pipeline package` takes the pipeline package version, rather than the kedro package version. If the pipeline package version is not present, then the package version is used.
* Launched [GitHub Discussions](https://github.com/kedro-org/kedro/discussions/) and [Kedro Discord Server](https://discord.gg/akJDeVaxnB)
* Improved error message when versioning is enabled for a dataset previously saved as non-versioned ([Issue #625](https://github.com/kedro-org/kedro/issues/625)).

## Minor breaking changes to the API

## Upcoming deprecations for Kedro 0.18.0

## Thanks for supporting contributions
[Lou Kratz](https://github.com/lou-k),
[Lucas Jamar](https://github.com/lucasjamar)

# Release 0.17.3

## Major features and improvements
* Kedro plugins can now override built-in CLI commands.
* Added a `before_command_run` hook for plugins to add extra behaviour before Kedro CLI commands run.
* `pipelines` from `pipeline_registry.py` and `register_pipeline` hooks are now loaded lazily when they are first accessed, not on startup:

    ```python
    from kedro.framework.project import pipelines

    print(pipelines["__default__"])  # pipeline loading is only triggered here
    ```

## Bug fixes and other changes
* `TemplatedConfigLoader` now correctly inserts default values when no globals are supplied.
* Fixed a bug where the `KEDRO_ENV` environment variable had no effect on instantiating the `context` variable in an iPython session or a Jupyter notebook.
* Plugins with empty CLI groups are no longer displayed in the Kedro CLI help screen.
* Duplicate commands will no longer appear twice in the Kedro CLI help screen.
* CLI commands from sources with the same name will show under one list in the help screen.
* The setup of a Kedro project, including adding src to path and configuring settings, is now handled via the `bootstrap_project` method.
* `configure_project` is invoked if a `package_name` is supplied to `KedroSession.create`. This is added for backward-compatibility purpose to support a workflow that creates `Session` manually. It will be removed in `0.18.0`.
* Stopped swallowing up all `ModuleNotFoundError` if `register_pipelines` not found, so that a more helpful error message will appear when a dependency is missing, e.g. [Issue #722](https://github.com/kedro-org/kedro/issues/722).
* When `kedro new` is invoked using a configuration yaml file, `output_dir` is no longer a required key; by default the current working directory will be used.
* When `kedro new` is invoked using a configuration yaml file, the appropriate `prompts.yml` file is now used for validating the provided configuration. Previously, validation was always performed against the kedro project template `prompts.yml` file.
* When a relative path to a starter template is provided, `kedro new` now generates user prompts to obtain configuration rather than supplying empty configuration.
* Fixed error when using starters on Windows with Python 3.7 (Issue [#722](https://github.com/kedro-org/kedro/issues/722)).
* Fixed decoding error of config files that contain accented characters by opening them for reading in UTF-8.
* Fixed an issue where `after_dataset_loaded` run would finish before a dataset is actually loaded when using `--async` flag.

## Upcoming deprecations for Kedro 0.18.0

* `kedro.versioning.journal.Journal` will be removed.
* The following properties on `kedro.framework.context.KedroContext` will be removed:
  * `io` in favour of `KedroContext.catalog`
  * `pipeline` (equivalent to `pipelines["__default__"]`)
  * `pipelines` in favour of `kedro.framework.project.pipelines`

# Release 0.17.2

## Major features and improvements
* Added support for `compress_pickle` backend to `PickleDataSet`.
* Enabled loading pipelines without creating a `KedroContext` instance:

    ```python
    from kedro.framework.project import pipelines

    print(pipelines)
    ```

* Projects generated with kedro>=0.17.2:
  - should define pipelines in `pipeline_registry.py` rather than `hooks.py`.
  - when run as a package, will behave the same as `kedro run`

## Bug fixes and other changes
* If `settings.py` is not importable, the errors will be surfaced earlier in the process, rather than at runtime.

## Minor breaking changes to the API
* `kedro pipeline list` and `kedro pipeline describe` no longer accept redundant `--env` parameter.
* `from kedro.framework.cli.cli import cli` no longer includes the `new` and `starter` commands.

## Upcoming deprecations for Kedro 0.18.0

* `kedro.framework.context.KedroContext.run` will be removed in release 0.18.0.

## Thanks for supporting contributions
[Sasaki Takeru](https://github.com/takeru)

# Release 0.17.1

## Major features and improvements
* Added `env` and `extra_params` to `reload_kedro()` line magic.
* Extended the `pipeline()` API to allow strings and sets of strings as `inputs` and `outputs`, to specify when a dataset name remains the same (not namespaced).
* Added the ability to add custom prompts with regexp validator for starters by repurposing `default_config.yml` as `prompts.yml`.
* Added the `env` and `extra_params` arguments to `register_config_loader` hook.
* Refactored the way `settings` are loaded. You will now be able to run:

    ```python
    from kedro.framework.project import settings

    print(settings.CONF_ROOT)
    ```

* Added a check on `kedro.runner.parallel_runner.ParallelRunner` which checks datasets for the `_SINGLE_PROCESS` attribute in the `_validate_catalog` method. If this attribute is set to `True` in an instance of a dataset (e.g. `SparkDataSet`), the `ParallelRunner` will raise an `AttributeError`.
* Any user-defined dataset that should not be used with `ParallelRunner` may now have the `_SINGLE_PROCESS` attribute set to `True`.

## Bug fixes and other changes
* The version of a packaged modular pipeline now defaults to the version of the project package.
* Added fix to prevent new lines being added to pandas CSV datasets.
* Fixed issue with loading a versioned `SparkDataSet` in the interactive workflow.
* Kedro CLI now checks `pyproject.toml` for a `tool.kedro` section before treating the project as a Kedro project.
* Added fix to `DataCatalog::shallow_copy` now it should copy layers.
* `kedro pipeline pull` now uses `pip download` for protocols that are not supported by `fsspec`.
* Cleaned up documentation to fix broken links and rewrite permanently redirected ones.
* Added a `jsonschema` schema definition for the Kedro 0.17 catalog.
* `kedro install` now waits on Windows until all the requirements are installed.
* Exposed `--to-outputs` option in the CLI, throughout the codebase, and as part of hooks specifications.
* Fixed a bug where `ParquetDataSet` wasn't creating parent directories on the fly.
* Updated documentation.

## Breaking changes to the API
* This release has broken the `kedro ipython` and `kedro jupyter` workflows. To fix this, follow the instructions in the migration guide below.
* You will also need to upgrade `kedro-viz` to 3.10.1 if you use the `%run_viz` line magic in Jupyter Notebook.

> *Note:* If you're using the `ipython` [extension](https://docs.kedro.org/en/0.17.1/11_tools_integration/02_ipython.html#ipython-extension) instead, you will not encounter this problem.

## Migration guide
You will have to update the file `<your_project>/.ipython/profile_default/startup/00-kedro-init.py` in order to make `kedro ipython` and/or `kedro jupyter` work. Add the following line before the `KedroSession` is created:

```python
configure_project(metadata.package_name)  # to add

session = KedroSession.create(metadata.package_name, path)
```

Make sure that the associated import is provided in the same place as others in the file:

```python
from kedro.framework.project import configure_project  # to add
from kedro.framework.session import KedroSession
```

## Thanks for supporting contributions
[Mariana Silva](https://github.com/marianansilva),
[Kiyohito Kunii](https://github.com/921kiyo),
[noklam](https://github.com/noklam),
[Ivan Doroshenko](https://github.com/imdoroshenko),
[Zain Patel](https://github.com/mzjp2),
[Deepyaman Datta](https://github.com/deepyaman),
[Sam Hiscox](https://github.com/samhiscoxqb),
[Pascal Brokmeier](https://github.com/pascalwhoop)

# Release 0.17.0

## Major features and improvements

* In a significant change, [we have introduced `KedroSession`](https://docs.kedro.org/en/0.17.0/04_kedro_project_setup/03_session.html) which is responsible for managing the lifecycle of a Kedro run.
* Created a new Kedro Starter: `kedro new --starter=mini-kedro`. It is possible to [use the DataCatalog as a standalone component](https://github.com/kedro-org/kedro-starters/tree/master/mini-kedro) in a Jupyter notebook and transition into the rest of the Kedro framework.
* Added `DatasetSpecs` with Hooks to run before and after datasets are loaded from/saved to the catalog.
* Added a command: `kedro catalog create`. For a registered pipeline, it creates a `<conf_root>/<env>/catalog/<pipeline_name>.yml` configuration file with `MemoryDataSet` datasets for each dataset that is missing from `DataCatalog`.
* Added `settings.py` and `pyproject.toml` (to replace `.kedro.yml`) for project configuration, in line with Python best practice.
* `ProjectContext` is no longer needed, unless for very complex customisations. `KedroContext`, `ProjectHooks` and `settings.py` together implement sensible default behaviour. As a result `context_path` is also now an _optional_ key in `pyproject.toml`.
* Removed `ProjectContext` from `src/<package_name>/run.py`.
* `TemplatedConfigLoader` now supports [Jinja2 template syntax](https://jinja.palletsprojects.com/en/2.11.x/templates/) alongside its original syntax.
* Made [registration Hooks](https://docs.kedro.org/en/0.17.0/07_extend_kedro/02_hooks.html#registration-hooks) mandatory, as the only way to customise the `ConfigLoader` or the `DataCatalog` used in a project. If no such Hook is provided in `src/<package_name>/hooks.py`, a `KedroContextError` is raised. There are sensible defaults defined in any project generated with Kedro >= 0.16.5.

## Bug fixes and other changes

* `ParallelRunner` no longer results in a run failure, when triggered from a notebook, if the run is started using `KedroSession` (`session.run()`).
* `before_node_run` can now overwrite node inputs by returning a dictionary with the corresponding updates.
* Added minimal, black-compatible flake8 configuration to the project template.
* Moved `isort` and `pytest` configuration from `<project_root>/setup.cfg` to `<project_root>/pyproject.toml`.
* Extra parameters are no longer incorrectly passed from `KedroSession` to `KedroContext`.
* Relaxed `pyspark` requirements to allow for installation of `pyspark` 3.0.
* Added a `--fs-args` option to the `kedro pipeline pull` command to specify configuration options for the `fsspec` filesystem arguments used when pulling modular pipelines from non-PyPI locations.
* Bumped maximum required `fsspec` version to 0.9.
* Bumped maximum supported `s3fs` version to 0.5 (`S3FileSystem` interface has changed since 0.4.1 version).

## Deprecations
* In Kedro 0.17.0 we have deleted the deprecated `kedro.cli` and `kedro.context` modules in favour of `kedro.framework.cli` and `kedro.framework.context` respectively.

## Other breaking changes to the API
* `kedro.io.DataCatalog.exists()` returns `False` when the dataset does not exist, as opposed to raising an exception.
* The pipeline-specific `catalog.yml` file is no longer automatically created for modular pipelines when running `kedro pipeline create`. Use `kedro catalog create` to replace this functionality.
* Removed `include_examples` prompt from `kedro new`. To generate boilerplate example code, you should use a Kedro starter.
* Changed the `--verbose` flag from a global command to a project-specific command flag (e.g `kedro --verbose new` becomes `kedro new --verbose`).
* Dropped support of the `dataset_credentials` key in credentials in `PartitionedDataSet`.
* `get_source_dir()` was removed from `kedro/framework/cli/utils.py`.
* Dropped support of `get_config`, `create_catalog`, `create_pipeline`, `template_version`, `project_name` and `project_path` keys by `get_project_context()` function (`kedro/framework/cli/cli.py`).
* `kedro new --starter` now defaults to fetching the starter template matching the installed Kedro version.
* Renamed `kedro_cli.py` to `cli.py` and moved it inside the Python package (`src/<package_name>/`), for a better packaging and deployment experience.
* Removed `.kedro.yml` from the project template and replaced it with `pyproject.toml`.
* Removed `KEDRO_CONFIGS` constant (previously residing in `kedro.framework.context.context`).
* Modified `kedro pipeline create` CLI command to add a boilerplate parameter config file in `conf/<env>/parameters/<pipeline_name>.yml` instead of `conf/<env>/pipelines/<pipeline_name>/parameters.yml`. CLI commands `kedro pipeline delete` / `package` / `pull` were updated accordingly.
* Removed `get_static_project_data` from `kedro.framework.context`.
* Removed `KedroContext.static_data`.
* The `KedroContext` constructor now takes `package_name` as first argument.
* Replaced `context` property on `KedroSession` with `load_context()` method.
* Renamed `_push_session` and `_pop_session` in `kedro.framework.session.session` to `_activate_session` and `_deactivate_session` respectively.
* Custom context class is set via `CONTEXT_CLASS` variable in `src/<your_project>/settings.py`.
* Removed `KedroContext.hooks` attribute. Instead, hooks should be registered in `src/<your_project>/settings.py` under the `HOOKS` key.
* Restricted names given to nodes to match the regex pattern `[\w\.-]+$`.
* Removed `KedroContext._create_config_loader()` and `KedroContext._create_data_catalog()`. They have been replaced by registration hooks, namely `register_config_loader()` and `register_catalog()` (see also [upcoming deprecations](#upcoming_deprecations_for_kedro_0.18.0)).


## Upcoming deprecations for Kedro 0.18.0

* `kedro.framework.context.load_context` will be removed in release 0.18.0.
* `kedro.framework.cli.get_project_context` will be removed in release 0.18.0.
* We've added a `DeprecationWarning` to the decorator API for both `node` and `pipeline`. These will be removed in release 0.18.0. Use Hooks to extend a node's behaviour instead.
* We've added a `DeprecationWarning` to the Transformers API when adding a transformer to the catalog. These will be removed in release 0.18.0. Use Hooks to customise the `load` and `save` methods.

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman),
[Zach Schuster](https://github.com/zschuster)

## Migration guide from Kedro 0.16.* to 0.17.*

**Reminder:** Our documentation on [how to upgrade Kedro](https://docs.kedro.org/en/0.17.0/12_faq/01_faq.html#how-do-i-upgrade-kedro) covers a few key things to remember when updating any Kedro version.

The Kedro 0.17.0 release contains some breaking changes. If you update Kedro to 0.17.0 and then try to work with projects created against earlier versions of Kedro, you may encounter some issues when trying to run `kedro` commands in the terminal for that project. Here's a short guide to getting your projects running against the new version of Kedro.


>*Note*: As always, if you hit any problems, please check out our documentation:
>* [How can I find out more about Kedro?](https://docs.kedro.org/en/0.17.0/12_faq/01_faq.html#how-can-i-find-out-more-about-kedro)
>* [How can I get my questions answered?](https://docs.kedro.org/en/0.17.0/12_faq/01_faq.html#how-can-i-get-my-question-answered).

To get an existing Kedro project to work after you upgrade to Kedro 0.17.0, we recommend that you create a new project against Kedro 0.17.0 and move the code from your existing project into it. Let's go through the changes, but first, note that if you create a new Kedro project with Kedro 0.17.0 you will not be asked whether you want to include the boilerplate code for the Iris dataset example. We've removed this option (you should now use a Kedro starter if you want to create a project that is pre-populated with code).

To create a new, blank Kedro 0.17.0 project to drop your existing code into, you can create one, as always, with `kedro new`. We also recommend creating a new virtual environment for your new project, or you might run into conflicts with existing dependencies.

* **Update `pyproject.toml`**: Copy the following three keys from the `.kedro.yml` of your existing Kedro project into the `pyproject.toml` file of your new Kedro 0.17.0 project:


    ```toml
    [tools.kedro]
    package_name = "<package_name>"
    project_name = "<project_name>"
    project_version = "0.17.0"
    ```

Check your source directory. If you defined a different source directory (`source_dir`), make sure you also move that to `pyproject.toml`.


* **Copy files from your existing project**:

  + Copy subfolders of `project/src/project_name/pipelines` from existing to new project
  + Copy subfolders of `project/src/test/pipelines` from existing to new project
  + Copy the requirements your project needs into `requirements.txt` and/or `requirements.in`.
  + Copy your project configuration from the `conf` folder. Take note of the new locations needed for modular pipeline configuration (move it from `conf/<env>/pipeline_name/catalog.yml` to `conf/<env>/catalog/pipeline_name.yml` and likewise for `parameters.yml`).
  + Copy from the `data/` folder of your existing project, if needed, into the same location in your new project.
  + Copy any Hooks from `src/<package_name>/hooks.py`.

* **Update your new project's README and docs as necessary**.

* **Update `settings.py`**: For example, if you specified additional Hook implementations in `hooks`, or listed plugins under `disable_hooks_by_plugin` in your `.kedro.yml`, you will need to move them to `settings.py` accordingly:

    ```python
    from <package_name>.hooks import MyCustomHooks, ProjectHooks

    HOOKS = (ProjectHooks(), MyCustomHooks())

    DISABLE_HOOKS_FOR_PLUGINS = ("my_plugin1",)
    ```

* **Migration for `node` names**. From 0.17.0 the only allowed characters for node names are letters, digits, hyphens, underscores and/or fullstops. If you have previously defined node names that have special characters, spaces or other characters that are no longer permitted, you will need to rename those nodes.

* **Copy changes to `kedro_cli.py`**. If you previously customised the `kedro run` command or added more CLI commands to your `kedro_cli.py`, you should move them into `<project_root>/src/<package_name>/cli.py`. Note, however, that the new way to run a Kedro pipeline is via a `KedroSession`, rather than using the `KedroContext`:

    ```python
    with KedroSession.create(package_name=...) as session:
        session.run()
    ```

* **Copy changes made to `ConfigLoader`**. If you have defined a custom class, such as `TemplatedConfigLoader`, by overriding `ProjectContext._create_config_loader`, you should move the contents of the function in `src/<package_name>/hooks.py`, under `register_config_loader`.

* **Copy changes made to `DataCatalog`**. Likewise, if you have `DataCatalog` defined with `ProjectContext._create_catalog`, you should copy-paste the contents into `register_catalog`.

* **Optional**: If you have plugins such as [Kedro-Viz](https://github.com/kedro-org/kedro-viz) installed, it's likely that Kedro 0.17.0 won't work with their older versions, so please either upgrade to the plugin's newest version or follow their migration guides.

# Release 0.16.6

## Major features and improvements

* Added documentation with a focus on single machine and distributed environment deployment; the series includes Docker, Argo, Prefect, Kubeflow, AWS Batch, AWS Sagemaker and extends our section on Databricks.
* Added [kedro-starter-spaceflights](https://github.com/kedro-org/kedro-starter-spaceflights/) alias for generating a project: `kedro new --starter spaceflights`.

## Bug fixes and other changes
* Fixed `TypeError` when converting dict inputs to a node made from a wrapped `partial` function.
* `PartitionedDataSet` improvements:
  - Supported passing arguments to the underlying filesystem.
* Improved handling of non-ASCII word characters in dataset names.
  - For example, a dataset named `jalapeño` will be accessible as `DataCatalog.datasets.jalapeño` rather than `DataCatalog.datasets.jalape__o`.
* Fixed `kedro install` for an Anaconda environment defined in `environment.yml`.
* Fixed backwards compatibility with templates generated with older Kedro versions <0.16.5. No longer need to update `.kedro.yml` to use `kedro lint` and `kedro jupyter notebook convert`.
* Improved documentation.
* Added documentation using MinIO with Kedro.
* Improved error messages for incorrect parameters passed into a node.
* Fixed issue with saving a `TensorFlowModelDataset` in the HDF5 format with versioning enabled.
* Added missing `run_result` argument in `after_pipeline_run` Hooks spec.
* Fixed a bug in IPython script that was causing context hooks to be registered twice. To apply this fix to a project generated with an older Kedro version, apply the same changes made in [this PR](https://github.com/kedro-org/kedro-starter-pandas-iris/pull/16) to your `00-kedro-init.py` file.
* Improved documentation.

## Breaking changes to the API

## Thanks for supporting contributions
[Deepyaman Datta](https://github.com/deepyaman), [Bhavya Merchant](https://github.com/bnmerchant), [Lovkush Agarwal](https://github.com/Lovkush-A), [Varun Krishna S](https://github.com/vhawk19), [Sebastian Bertoli](https://github.com/sebastianbertoli), [noklam](https://github.com/noklam), [Daniel Petti](https://github.com/djpetti), [Waylon Walker](https://github.com/waylonwalker), [Saran Balaji C](https://github.com/csaranbalaji)

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
These can be defined in `src/<python_package>/hooks.py` and added to `.kedro.yml` (or `pyproject.toml`). The order of execution is: plugin hooks, `.kedro.yml` hooks, hooks in `ProjectContext.hooks`.
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
project_version: "<kedro_version_of_the_project>"
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
* `DataCatalog` improvements:
  - Introduced regex filtering to the `DataCatalog.list()` method.
  - Non-alphanumeric characters (except underscore) in dataset name are replaced with `__` in `DataCatalog.datasets`, for ease of access to transcoded datasets.
* Dataset improvements:
  - Improved initialization speed of `spark.SparkHiveDataSet`.
  - Improved S3 cache in `spark.SparkDataSet`.
  - Added support of options for building `pyarrow` table in `pandas.ParquetDataSet`.
* `kedro build-reqs` CLI command improvements:
  - `kedro build-reqs` is now called with `-q` option and will no longer print out compiled requirements to the console for security reasons.
  - All unrecognized CLI options in `kedro build-reqs` command are now passed to [pip-compile](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) call (e.g. `kedro build-reqs --generate-hashes`).
* `kedro jupyter` CLI command improvements:
  - Improved error message when running `kedro jupyter notebook`, `kedro jupyter lab` or `kedro ipython` with Jupyter/IPython dependencies not being installed.
  - Fixed `%run_viz` line magic for showing kedro viz inside a Jupyter notebook. For the fix to be applied on existing Kedro project, please see the migration guide.
  - Fixed the bug in IPython startup script ([issue 298](https://github.com/kedro-org/kedro/issues/298)).
* Documentation improvements:
  - Updated community-generated content in FAQ.
  - Added [find-kedro](https://github.com/WaylonWalker/find-kedro) and [kedro-static-viz](https://github.com/WaylonWalker/kedro-static-viz) to the list of community plugins.
  - Add missing `pillow.ImageDataSet` entry to the documentation.

## Breaking changes to the API

### Migration guide from Kedro 0.16.1 to 0.16.2

#### Guide to apply the fix for `%run_viz` line magic in existing project

Even though this release ships a fix for project generated with `kedro==0.16.2`, after upgrading, you will still need to make a change in your existing project if it was generated with `kedro>=0.16.0,<=0.16.1` for the fix to take effect. Specifically, please change the content of your project's IPython init script located at `.ipython/profile_default/startup/00-kedro-init.py` with the content of [this file](https://github.com/kedro-org/kedro/blob/0.16.2/kedro/templates/project/%7B%7B%20cookiecutter.repo_name%20%7D%7D/.ipython/profile_default/startup/00-kedro-init.py). You will also need `kedro-viz>=3.3.1`.

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
* Added the ability to specify extra arguments, e.g. `encoding` or `compression`, for `fsspec.spec.AbstractFileSystem.open()` calls when loading/saving a dataset. See Example 3 under [docs](https://docs.kedro.org/en/0.16.0/04_user_guide/04_data_catalog.html#use-the-data-catalog-with-the-yaml-api).

### Other
* Added `namespace` property on ``Node``, related to the modular pipeline where the node belongs.
* Added an option to enable asynchronous loading inputs and saving outputs in both `SequentialRunner(is_async=True)` and `ParallelRunner(is_async=True)` class.
* Added `MemoryProfiler` transformer.
* Removed the requirement to have all dependencies for a dataset module to use only a subset of the datasets within.
* Added support for `pandas>=1.0`.
* Enabled Python 3.8 compatibility. _Please note that a Spark workflow may be unreliable for this Python version as `pyspark` is not fully-compatible with 3.8 yet._
* Renamed "features" layer to "feature" layer to be consistent with (most) other layers and the [relevant FAQ](https://docs.kedro.org/en/0.16.0/06_resources/01_faq.html#what-is-data-engineering-convention).

## Bug fixes and other changes
* Fixed a bug where a new version created mid-run by an external system caused inconsistencies in the load versions used in the current run.
* Documentation improvements
  * Added instruction in the documentation on how to create a custom runner).
  * Updated contribution process in `CONTRIBUTING.md` - added Developer Workflow.
  * Documented installation of development version of Kedro in the [FAQ section](https://docs.kedro.org/en/0.16.0/06_resources/01_faq.html#how-can-i-use-development-version-of-kedro).
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

**reminder** [How do I upgrade Kedro](https://docs.kedro.org/en/0.16.0/06_resources/01_faq.html#how-do-i-upgrade-kedro) covers a few key things to remember when updating any kedro version.

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
    prefix="pre",
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
    namespace="pre",
)
```

#### Migration for decorators, color logger, transformers etc.
Since some modules were moved to other locations you need to update import paths appropriately.
You can find the list of moved files in the [`0.15.6` release notes](https://github.com/kedro-org/kedro/releases/tag/0.15.6) under the section titled `Files with a new location`.

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
> _TL;DR_ We're launching [`kedro.extras`](https://github.com/kedro-org/kedro/tree/master/extras), the new home for our revamped series of datasets, decorators and dataset transformers. The datasets in [`kedro.extras.datasets`](https://github.com/kedro-org/kedro/tree/master/extras/datasets) use [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to access a variety of data stores including local file systems, network file systems, cloud object stores (including S3 and GCP), and Hadoop, read more about this [**here**](https://docs.kedro.org/en/0.15.6/04_user_guide/04_data_catalog.html#specifying-the-location-of-the-dataset). The change will allow [#178](https://github.com/kedro-org/kedro/issues/178) to happen in the next major release of Kedro.

An example of this new system can be seen below, loading the CSV `SparkDataSet` from S3:

```yaml
weather:
  type: spark.SparkDataSet  # Observe the specified type, this  affects all datasets
  filepath: s3a://your_bucket/data/01_raw/weather*  # filepath uses fsspec to indicate the file storage system
  credentials: dev_s3
  file_format: csv
```

You can also load data incrementally whenever it is dumped into a directory with the extension to [`PartionedDataSet`](https://docs.kedro.org/en/0.15.6/04_user_guide/08_advanced_io.html#partitioned-dataset), a feature that allows you to load a directory of files. The [`IncrementalDataSet`](https://docs.kedro.org/en/0.15.6/04_user_guide/08_advanced_io.html#incremental-loads-with-incrementaldataset) stores the information about the last processed partition in a `checkpoint`, read more about this feature [**here**](https://docs.kedro.org/en/0.15.6/04_user_guide/08_advanced_io.html#incremental-loads-with-incrementaldataset).

### New features

* Added `layer` attribute for datasets in `kedro.extras.datasets` to specify the name of a layer according to [data engineering convention](https://docs.kedro.org/en/0.15.6/06_resources/01_faq.html#what-is-data-engineering-convention), this feature will be passed to [`kedro-viz`](https://github.com/kedro-org/kedro-viz) in future releases.
* Enabled loading a particular version of a dataset in Jupyter Notebooks and iPython, using `catalog.load("dataset_name", version="<2019-12-13T15.08.09.255Z>")`.
* Added property `run_id` on `ProjectContext`, used for versioning using the [`Journal`](https://docs.kedro.org/en/0.15.6/04_user_guide/13_journal.html). To customise your journal `run_id` you can override the private method `_get_run_id()`.
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
  - Lint your project code using the `kedro lint` command, your project is linted with [`black`](https://github.com/psf/black) (Python 3.6+), [`flake8`](https://gitlab.com/pycqa/flake8) and [`isort`](https://github.com/PyCQA/isort).
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
* Added Jupyter Notebook line magic (`%run_viz`) to run `kedro viz` in a Notebook cell (requires [`kedro-viz`](https://github.com/kedro-org/kedro-viz) version 3.0.0 or later).
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
- `<project-name>/src/<python_package>/run.py`
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

These steps should have brought your project to Kedro 0.15.0. There might be some more minor tweaks needed as every project is unique, but now you have a pretty solid base to work with. If you run into any problems, please consult the [Kedro documentation](https://docs.kedro.org).

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
