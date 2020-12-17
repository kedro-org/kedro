# Kedro architecture overview


> *Note:* This documentation is based on `Kedro 0.17.0`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

Here is a diagram showing high-level architecture of Kedro library:

![Kedro architecture diagram](../meta/images/kedro_architecture.png)

> *Note:* The arrow `A -> B` on the diagram above should be read as: _"A is aware of existence of B or directly uses B, while B does not necessarily know about A"_.

> *Note:* Internally we use [import-linter](https://github.com/seddonym/import-linter/) to enforce this structure and generally want the lower layer to be unaware of the above layers.

## Building blocks

The architecture diagram above is formed of the following building blocks:

### Project

This section contains the building blocks that help accessing core components of the Kedro project (e.g., the data catalog or the pipeline).

#### `cli.py`

A Python file that contains project specific CLI commands (e.g., `kedro run`, `kedro test`, etc.). This file must be located at the root of the project.

#### `run.py`

A Python file located in `src/<python_package>/run.py`. This file serves as the main entry point of the project and is used to run the project in [package mode](../03_tutorial/05_package_a_project.md#package-your-project).

#### `pyproject.toml`

`pyproject.yml` identifies the project root, which is used by other Kedro components and contains the following metadata entries:
- `package_name`: A valid Python package name for your project package
- `project_name`: A human readable name for your project
- `project_version`: Kedro version with which the project was generated
- `source_dir`: (Optional) The directory of the source path relative to the project root path. Default directory is `src/` and when customised the path should be separated by a forward slash (e.g `src/<path_to_src>/`)

`pyproject.toml` must be located at the root of the project. We use the `pyproject.toml` for all configuration needed to create the Python package and allow the Kedro CLI to find where the source code is.

#### `settings.py`

We use the `settings.py` for all project settings, which will not change at run time, but at development time. `settings.py` contains the following configuration entries:

- `DISABLE_HOOKS_FOR_PLUGINS`: (Optional, `tuple`) A list of the installed plugins for which to disable auto-registry
- `HOOKS`: (Optional, `tuple`) A list of instances of [Hooks](../07_extend_kedro/02_hooks.md) implementations to be registered with the project (default is an instance of `<python_project>.hooks.ProjectHooks`)
- `SESSION_STORE_CLASS`: (Optional, `class`) Define a store class to be used to save data from a `KedroSession`
- `SESSION_STORE_ARGS`: (Optional, `dict`) Define keyword arguments to be passed to `SESSION_STORE_CLASS` constructor
- `CONTEXT_CLASS`: (Optional, `class`) Define a project context class to be used at runtime. Defaults to `KedroContext` class

#### `00-kedro-init.py`

This script is automatically invoked at IPython kernel startup when calling `kedro jupyter notebook`, `kedro jupyter lab` and `kedro ipython` CLI commands. `00-kedro-init.py` creates an instance of `KedroContext` object, which can be used to interact with the current project right away.

### Framework

This section contains the building blocks that help running native Kedro and plugin CLI commands.

#### `kedro cli`

Any Kedro CLI command (e.g., `kedro new`, `kedro run`) executed by a user.

#### `kedro/cli/cli.py`

A Python file that contains Kedro global CLI commands, i.e. the ones that do not require a Kedro project in the current working directory to work (e.g., `kedro new`, `kedro info`).

#### `plugins`

Any CLI command that is implemented by a [Kedro plugin](../07_extend_kedro/04_plugins.md) (e.g., [Kedro-Docker](https://github.com/quantumblacklabs/kedro-docker), [Kedro-Airflow](https://github.com/quantumblacklabs/kedro-airflow), [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz)).

#### `get_project_context()`

A python function that instantiates the project context by calling `load_context()`. `get_project_context()` also preserves backwards compatible interface to ensure old versions of the plugins continue working even if breaking changes are introduced in `load_context()`.

> *Note:* This function is intended for plugin use only. It is now deprecated and will be removed in version 0.18.0. To instantiate the project context outside of a plugin, you should call `KedroSession.load_context()`.

#### `load_context()`

> *Note:* This function is now deprecated in favour of `KedroSession.load_context()` and will be removed in Kedro 0.18.0.

A Python function that locates Kedro project based on `pyproject.toml` and instantiates the project context.

#### `KedroSession`

`KedroSession` is the object that is responsible for managing the lifecycle of a Kedro run.

#### `KedroContext`

The base class for project context implementations. It holds the configuration and Kedro's main functionality, and also serves the purpose of the main entry point for interactions with the core project components.

### Library

This section lists core Kedro components. These library components can be used both in conjunction and separately.

#### `ConfigLoader`

Helper class that enables loading the project configuration in a consistent way.

#### `Pipeline`

A collection of `Node` objects with the preserved execution order.

#### `AbstractRunner`

A base class for all `Pipeline` runner implementations.

#### `DataCatalog`

A dataset store providing `load` and `save` capabilities for the underlying datasets.

#### `AbstractDataSet`

A base class for all dataset implementations.
