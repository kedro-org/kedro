# Project settings

A Kedro project's `settings.py` file contains the application settings for the project, including registration of Hooks and library components. This page explains how settings work, and which settings are available.

```{note}
Application settings is distinct from [run time configuration](configuration.md), which is stored in the `conf` folder and can vary by configuration environment, and [pyproject.toml](../faq/architecture_overview.md#kedro-project) , which provides project metadata and build configuration.
```

By default, all code in `settings.py` is commented out. When settings are not supplied, Kedro chooses sensible default values. You only need to edit `settings.py` if you wish to change to values other than the defaults.

| Setting                     | Default value                                     | Use                                                                                                                |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `HOOKS`                     | `tuple()`                                         | Inject additional behaviour into the execution timeline with [project Hooks](../hooks/introduction.md).            |
| `DISABLE_HOOKS_FOR_PLUGINS` | `tuple()`                                         | Disable [auto-registration of Hooks from plugins](../hooks/introduction.md#disable-auto-registered-plugins-hooks). |
| `SESSION_STORE_CLASS`       | `kedro.framework.session.session.BaseSessionStore`| Customise how [session data](session.md) is stored.                                                                |
| `SESSION_STORE_ARGS`        | `dict()`                                          | Keyword arguments for the `SESSION_STORE_CLASS` constructor.                                                       |
| `CONTEXT_CLASS`             | `kedro.framework.context.KedroContext`            | Customise how Kedro library components are managed.                                                                |
| `CONF_SOURCE`               | `"conf"`                                          | Directory that holds [configuration](configuration.md).                                                            |
| `CONFIG_LOADER_CLASS`       | `kedro.config.ConfigLoader`                       | Customise how project configuration is handled.                                                                    |
| `CONFIG_LOADER_ARGS`        | `dict()`                                          | Keyword arguments for the `CONFIG_LOADER_CLASS` constructor.                                                       |
| `DATA_CATALOG_CLASS`        | `kedro.io.DataCatalog`                            | Customise how the [Data Catalog](../data/data_catalog.md) is handled.                                              |
