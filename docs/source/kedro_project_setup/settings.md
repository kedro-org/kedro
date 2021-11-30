# Project settings

A Kedro project's `settings.py` file contains the runtime configuration for the project, including registration of hooks and library components. This page explains how settings work and which settings are available.

## Default settings
A Kedro settings file doesn’t have to define any settings if it doesn’t need to. Each setting has a sensible default value. These defaults live in the module `src/<project_name>/settings.py`.

## Available settings

#### HOOKS
Default: `tuple()`

Instantiate and list your project hooks.

```python
HOOKS = (ProjectHooks(),)
```

#### DISABLE_HOOKS_FOR_PLUGINS
Default: `tuple()`

List the installed plugins for which to disable auto-registry.

```python
DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)
```

#### SESSION_STORE_CLASS
Default: `kedro.framework.session.session.BaseSessionStore`

Define where to store data from a KedroSession.

```python
from kedro.framework.session.store import ShelveStore

SESSION_STORE_CLASS = ShelveStore
```

#### SESSION_STORE_ARGS
Default: { } (empty dictionary)

Define keyword arguments to be passed to `SESSION_STORE_CLASS` constructor.

```python
SESSION_STORE_ARGS = {"path": "./sessions"}
```

#### CONTEXT_CLASS
Default: `kedro.framework.context.KedroContext`

Define custom context class.
```python
from myproject import CustomContext

CONTEXT_CLASS = CustomContext
```

#### CONF_SOURCE
Define the configuration folder. Defaults to `conf`

```python
CONF_SOURCE = "conf"
```

#### CONFIG_LOADER_CLASS
Default: `kedro.config.ConfigLoader`

Define the project ConfigLoader class.

```python
from kedro.config import TemplatedConfigLoader

CONFIG_LOADER_CLASS = TemplatedConfigLoader
```

#### CONFIG_LOADER_ARGS
Default: { } (empty dictionary)

Define keyword arguments to be passed to `CONFIG_LOADER_CLASS` constructor. These kwargs depend on the `ConfigLoader` class implementation.

```python
CONFIG_LOADER_ARGS = {
    "globals_pattern": "*globals.yml",
    "base_env": "base",
    "default_run_env": "local",
}
```

#### DATA_CATALOG_CLASS
Default: `kedro.io.DataCatalog`

Define the project `DataCatalog` class.

```python
from myproject import CustomCatalog

DATA_CATALOG_CLASS = CustomCatalog
```
