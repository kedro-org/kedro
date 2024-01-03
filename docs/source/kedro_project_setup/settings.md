# Project settings

## Application settings

A Kedro project's `settings.py` file contains the application settings for the project, including registration of Hooks and library components. This page explains how settings work, and which settings are available.

```{note}
Application settings is distinct from [run time configuration](../configuration/configuration_basics.md), which is stored in the `conf` folder and can vary by configuration environment, and [pyproject.toml](#project-metadata) , which provides project metadata and build configuration.
```

By default, all code in `settings.py` is commented out. When settings are not supplied, Kedro chooses sensible default values. You only need to edit `settings.py` if you wish to change to values other than the defaults.

| Setting                     | Default value                                     | Use                                                                                                                |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `HOOKS`                     | `tuple()`                                         | Inject additional behaviour into the execution timeline with [project Hooks](../hooks/introduction.md).            |
| `DISABLE_HOOKS_FOR_PLUGINS` | `tuple()`                                         | Disable [auto-registration of Hooks from plugins](../hooks/introduction.md#disable-auto-registered-plugins-hooks). |
| `SESSION_STORE_CLASS`       | `kedro.framework.session.session.BaseSessionStore`| Customise how [session data](session.md) is stored.                                                                |
| `SESSION_STORE_ARGS`        | `dict()`                                          | Keyword arguments for the `SESSION_STORE_CLASS` constructor.                                                       |
| `CONTEXT_CLASS`             | `kedro.framework.context.KedroContext`            | Customise how Kedro library components are managed.                                                                |
| `CONF_SOURCE`               | `"conf"`                                          | Directory that holds [configuration](../configuration/configuration_basics.md).                                    |
| `CONFIG_LOADER_CLASS`       | `kedro.config.ConfigLoader`                       | Customise how project configuration is handled.                                                                    |
| `CONFIG_LOADER_ARGS`        | `dict()`                                          | Keyword arguments for the `CONFIG_LOADER_CLASS` constructor.                                                       |
| `DATA_CATALOG_CLASS`        | `kedro.io.DataCatalog`                            | Customise how the [Data Catalog](../data/data_catalog.md) is handled.                                              |

## Project metadata
The `pyproject.toml` file is the standard way to store build metadata and tool settings for Python projects.
Every Kedro project comes with a default pre-populated `pyproject.toml` file in your project root directory with the following keys specified under the `[tool.kedro]` section:

```toml
[tool.kedro]
package_name = "package_name"
project_name = "project_name"
kedro_init_version = "kedro_version"
tools = ""
source_dir = "src"
```

The `package_name` should be a [valid Python package name](https://peps.python.org/pep-0423/) and the `project_name` should be a human-readable name. They are both mandatory keys for your project.
`kedro_init_version` specifies the version of Kedro the project was created with. When you upgrade to a newer Kedro version,
this value should also be updated.

You can also use `pyproject.toml` to specify settings for functionalities such as [micro-packaging](../nodes_and_pipelines/micro_packaging.md).
You can also store the settings for the other tools you've used in your project, such as [`pytest` for automated testing](../development/automated_testing.md).
Consult the respective documentation for the tools you have used to check how you can configure the settings with the `pyproject.toml` file for your project.

### Use Kedro without the `src` folder
Kedro uses the `src` layout by default. It is possible to change this, for example, to use a [flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/#src-layout-vs-flat-layout), you can change the `pyproject.toml` as follow.

```diff
+++ source_dir = ""
--- source_dir = "src"
```
