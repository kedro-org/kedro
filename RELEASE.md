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
* Stopped swallowing up all `ModuleNotFoundError` if `register_pipelines` not found, so that a more helpful error message will appear when a dependency is missing, e.g. [Issue #722](https://github.com/quantumblacklabs/kedro/issues/722).
* When `kedro new` is invoked using a configuration yaml file, `output_dir` is no longer a required key; by default the current working directory will be used.
* When `kedro new` is invoked using a configuration yaml file, the appropriate `prompts.yml` file is now used for validating the provided configuration. Previously, validation was always performed against the kedro project template `prompts.yml` file.
* When a relative path to a starter template is provided, `kedro new` now generates user prompts to obtain configuration rather than supplying empty configuration.
* Fixed error when using starters on Windows with Python 3.7 (Issue [#722](https://github.com/quantumblacklabs/kedro/issues/722)).
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
[Sasaki Takeru](https://github.com/takeru/)

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

> *Note:* If you're using the `ipython` [extension](https://kedro.readthedocs.io/en/stable/11_tools_integration/02_ipython.html#ipython-extension) instead, you will not encounter this problem.

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

* In a significant change, [we have introduced `KedroSession`](https://kedro.readthedocs.io/en/stable/04_kedro_project_setup/03_session.html) which is responsible for managing the lifecycle of a Kedro run.
* Created a new Kedro Starter: `kedro new --starter=mini-kedro`. It is possible to [use the DataCatalog as a standalone component](https://github.com/quantumblacklabs/kedro-starters/tree/master/mini-kedro) in a Jupyter notebook and transition into the rest of the Kedro framework.
* Added `DatasetSpecs` with Hooks to run before and after datasets are loaded from/saved to the catalog.
* Added a command: `kedro catalog create`. For a registered pipeline, it creates a `<conf_root>/<env>/catalog/<pipeline_name>.yml` configuration file with `MemoryDataSet` datasets for each dataset that is missing from `DataCatalog`.
* Added `settings.py` and `pyproject.toml` (to replace `.kedro.yml`) for project configuration, in line with Python best practice.
* `ProjectContext` is no longer needed, unless for very complex customisations. `KedroContext`, `ProjectHooks` and `settings.py` together implement sensible default behaviour. As a result `context_path` is also now an _optional_ key in `pyproject.toml`.
* Removed `ProjectContext` from `src/<package_name>/run.py`.
* `TemplatedConfigLoader` now supports [Jinja2 template syntax](https://jinja.palletsprojects.com/en/2.11.x/templates/) alongside its original syntax.
* Made [registration Hooks](https://kedro.readthedocs.io/en/stable/07_extend_kedro/04_hooks.html#registration-hooks) mandatory, as the only way to customise the `ConfigLoader` or the `DataCatalog` used in a project. If no such Hook is provided in `src/<package_name>/hooks.py`, a `KedroContextError` is raised. There are sensible defaults defined in any project generated with Kedro >= 0.16.5.

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

**Reminder:** Our documentation on [how to upgrade Kedro](https://kedro.readthedocs.io/en/stable/12_faq/01_faq.html#how-do-i-upgrade-kedro) covers a few key things to remember when updating any Kedro version.

The Kedro 0.17.0 release contains some breaking changes. If you update Kedro to 0.17.0 and then try to work with projects created against earlier versions of Kedro, you may encounter some issues when trying to run `kedro` commands in the terminal for that project. Here's a short guide to getting your projects running against the new version of Kedro.


>*Note*: As always, if you hit any problems, please check out our documentation:
>* [How can I find out more about Kedro?](https://kedro.readthedocs.io/en/stable/12_faq/01_faq.html#how-can-i-find-out-more-about-kedro)
>* [How can I get my questions answered?](https://kedro.readthedocs.io/en/stable/12_faq/01_faq.html#how-can-i-get-my-question-answered).

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

* **Optional**: If you have plugins such as [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz) installed, it's likely that Kedro 0.17.0 won't work with their older versions, so please either upgrade to the plugin's newest version or follow their migration guides.

# Release 0.16.6

## Major features and improvements

* Added documentation with a focus on single machine and distributed environment deployment; the series includes Docker, Argo, Prefect, Kubeflow, AWS Batch, AWS Sagemaker and extends our section on Databricks
* Added [kedro-starter-spaceflights](https://github.com/quantumblacklabs/kedro-starter-spaceflights/) alias for generating a project: `kedro new --starter spaceflights`.

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
* Fixed a bug in IPython script that was causing context hooks to be registered twice. To apply this fix to a project generated with an older Kedro version, apply the same changes made in [this PR](https://github.com/quantumblacklabs/kedro-starter-pandas-iris/pull/16) to your `00-kedro-init.py` file.
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
