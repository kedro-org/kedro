# How to cache configuration

This guide shows how to cache configuration and resolve it with different runtime parameters using `LazyOmegaConfigLoader`. It assumes familiarity with [Kedro configuration](configuration_basics.md).

For the caching model and concurrency limitations, see [Caching configuration](caching_configuration.md). To update existing loader usage, see [Migrating from `OmegaConfigLoader`](config_loader_migration.md#omegaconfigloader-to-lazyomegaconfigloader).

## On this page

- [Configure the loader](#configure-the-loader)
- [Read configuration](#read-configuration)
- [Preload and resolve per run](#preload-and-resolve-per-run)
- [Inspect unresolved configuration](#inspect-unresolved-configuration)
- [Configuration lifetime](#configuration-lifetime)
- [Interpolation scope](#interpolation-scope)

!!! warning "Experimental status"

    `LazyOmegaConfigLoader` and its public methods are experimental and may change or be removed in a future Kedro release. Instantiating the loader emits a `KedroExperimentalWarning` once per process.

## Configure the loader

To opt in, set `CONFIG_LOADER_CLASS` and `CONFIG_LOADER_ARGS` in your project's `src/<package_name>/settings.py`:

```python
from kedro.config import LazyOmegaConfigLoader

CONFIG_LOADER_CLASS = LazyOmegaConfigLoader
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
}
```

`LazyOmegaConfigLoader` accepts the same file patterns, merge strategies, custom resolvers, and runtime-parameter type-selection option as `OmegaConfigLoader`. To go back to the default loader, remove these settings or set `CONFIG_LOADER_CLASS = OmegaConfigLoader`.

## Read configuration

Access a configuration key as you would with `OmegaConfigLoader`. For example,
given `conf/base/parameters.yml`:

```yaml
learning_rate: 0.1
```

Read the parameters with:

```python
from kedro.config import LazyOmegaConfigLoader

loader = LazyOmegaConfigLoader("conf", base_env="base", default_run_env="local")
loader["parameters"]
# {"learning_rate": 0.1}
```

The loader reads and caches the parsed configuration for a key on first
access, then resolves it into a Python dictionary. Later accesses reuse the
cached configuration without rereading the files. Unlike `OmegaConfigLoader`,
the loader doesn't pick up file changes on later accesses. Call `preload()`
or create a new loader to read the files again. Ensure that the configured
environment directories exist, even if they contain no matching files.

## Preload and resolve per run

Use `preload()` before serving repeated requests. It reads and caches the
configured files. It also resolves globals and credentials. Key
access and `with_runtime_params()` reuse the cache even if files change on
disk; call `preload()` again to read the files anew.

!!! warning "`preload()` refreshes files, not your overrides"

    Calling `preload()` again re-reads the configured files, but it doesn't reset the loader. Values you assigned, such as `loader["globals"] = ...`, still take precedence over values from files. The loader still reads and validates files for overridden keys, so an invalid file can cause preloading to fail.

    To use the file values again, delete the override with `del loader[key]` and call `preload()`.

    For example, with `bucket: "prod-bucket"` in `conf/base/globals.yml` and `path: "s3://${globals:bucket}"` in `conf/base/parameters.yml`:

    ```python
    loader["globals"] = {"bucket": "test-bucket"}
    loader.preload()
    loader["parameters"]  # {"path": "s3://test-bucket"}

    del loader["globals"]  # drop the override, so that the files are used again
    loader.preload()
    loader["parameters"]  # {"path": "s3://prod-bucket"}
    ```

Start with this `conf/base/parameters.yml`:

```yaml
report_label: "Report for ${runtime_params:customer_id}"
```

Then resolve the parameters separately for each run:

```python
from pathlib import Path

from kedro.config import LazyOmegaConfigLoader

project_path = Path("/path/to/project")
loader = LazyOmegaConfigLoader(
    conf_source=project_path / "conf",
    env="local",
    base_env="base",
    default_run_env="local",
)
loader.preload()

first_run = loader.with_runtime_params({"customer_id": "customer-001"})
second_run = loader.with_runtime_params({"customer_id": "customer-002"})

first_parameters = first_run["parameters"]
# {"report_label": "Report for customer-001", "customer_id": "customer-001"}
second_parameters = second_run["parameters"]
# {"report_label": "Report for customer-002", "customer_id": "customer-002"}
```

As with `OmegaConfigLoader`, the runtime parameters are also merged into `parameters`: `customer_id` appears in the result, and a runtime value replaces a YAML key with the same name. `KedroContext` reads runtime parameters from this result. The values stay available on the loader copy as `first_run.runtime_params`.

Each `with_runtime_params()` call returns a loader copy with replacement runtime
parameters and separate runtime-resolution state. The copies share the loader's
configuration caches, so they don't reread the files for each run. Nested
explicit override values can remain shared; see
[how the loader is copied](caching_configuration.md#repeated-runs).

!!! note

    The loader copy resolves configuration. It does not create a `KedroContext`, catalog, or run a pipeline. `KedroServiceSession` preloads the configured lazy loader and creates a copy for each run; see [use `LazyOmegaConfigLoader` with `KedroServiceSession`](../extend/session.md#use-lazyomegaconfigloader-with-kedroservicesession).

## Inspect unresolved configuration

Use `get_unresolved_config(key)` to inspect a read-only, merged `DictConfig`
without resolving its remaining interpolations. If you assigned an explicit
override to the key, the method returns a copy of that value instead.
Interpolations in credential files are resolved during file loading.
For example, given these files:

```yaml
# conf/base/parameters.yml
lr: 0.1
next_lr: "${lr}"
run: "${runtime_params:run_id, none}"
```

```yaml
# conf/local/parameters.yml
lr: 0.2
```

Inspect the raw merge and compare it with normal key access:

```python
from kedro.config import LazyOmegaConfigLoader
from omegaconf import OmegaConf

loader = LazyOmegaConfigLoader("conf", base_env="base", default_run_env="local")
raw = loader.get_unresolved_config("parameters")
OmegaConf.to_container(raw, resolve=False)
# {"lr": 0.2, "next_lr": "${lr}", "run": "${runtime_params:run_id, none}"}

loader["parameters"]
# {"lr": 0.2, "next_lr": 0.1, "run": "none"}

raw.lr = 1  # raises ReadonlyConfigError
```

The raw merge contains the local `lr` value, but normal key access resolves
`next_lr` within the base environment before merging. See
[Interpolation scope](#interpolation-scope) for details.

Use this method for inspection, not for resolving configuration. Read-only
doesn't prevent interpolation resolution, which can happen when you access
individual values. Use `OmegaConf.to_container(raw, resolve=False)` to inspect
the result, and `loader[key]` to resolve configuration through the loader.

## Configuration lifetime

The loader keeps its cached configuration until `preload()` is called again.
Each `preload()` call re-reads the files and replaces the cache; if reading
fails, the previous cache is kept. Key access and `with_runtime_params()`
reuse cached keys even if their YAML files change. Loader copies created before a new
`preload()` keep using the previous cache.

!!! warning "Credentials aren't resolved for each run"

    The loader resolves credentials once, when it first reads their files, with the runtime parameters passed to its constructor. Every loader copy reuses these credentials: `with_runtime_params()` doesn't change them, even when a credentials file uses `${runtime_params:...}`.

    ```yaml
    # conf/base/credentials.yml
    db:
      user: ${runtime_params:db_user, default_user}
    ```

    ```python
    loader = LazyOmegaConfigLoader("conf", base_env="base", default_run_env="local")
    loader.with_runtime_params({"db_user": "alice"})["credentials"]
    # {'db': {'user': 'default_user'}}
    ```

    An `OmegaConfigLoader` created with `runtime_params={"db_user": "alice"}` returns `alice` instead. Don't rely on runtime parameters to change credentials between runs. Pass values that change between runs through `with_runtime_params()` and the `runtime_params` resolver in parameters or catalog configuration.

## Interpolation scope

Lazy resolution and environment merge order are independent. `"environment"`, the default, preserves existing results; `"merged"` resolves interpolations against the combined environments.

| Value           | Behaviour                                                                           |
| --------------- | ----------------------------------------------------------------------------------- |
| `"environment"` | Resolve each environment before merging, matching `OmegaConfigLoader`. The default. |
| `"merged"`      | Merge the raw configuration from the environments, then resolve interpolations.     |

!!! warning "Keep the default unless you need different results"

    Keep the default `"environment"` scope unless you have a clear reason to
    change it. The `"merged"` scope can change configuration results. It can
    also be slower for a single cold CLI run because it does more merging up
    front. For repeated runs with different runtime parameters, it may be
    faster because the merged configuration can be reused. Measure your own
    workload before changing the scope for performance.

For example, given these files:

```yaml
# conf/base/parameters.yml
param1: "${param2}"
param2: "base"
```

```yaml
# conf/local/parameters.yml
param2: "local"
```

Compare the two scopes:

```python
from kedro.config import LazyOmegaConfigLoader

environment = LazyOmegaConfigLoader(
    "conf", base_env="base", default_run_env="local",
)
merged = LazyOmegaConfigLoader(
    "conf", base_env="base", default_run_env="local", interpolation_scope="merged",
)

environment["parameters"]
# {"param1": "base", "param2": "local"}
merged["parameters"]
# {"param1": "local", "param2": "local"}
```

The default resolves `param1` in the base environment before applying the
local override, as `OmegaConfigLoader` does. The `"merged"` scope resolves
`param1` after the override.

Both scopes merge `runtime_params` into `parameters`. The `"merged"` scope does so after merging environments, which can preserve base keys that the default destructive strategy replaces in `OmegaConfigLoader`.

For example, with `x: {a: 1}` in `conf/base/parameters.yml`, `y: 2` in `conf/local/parameters.yml`, and runtime parameters `{"x": {"b": 5}}`, the results differ:

| Scope           | Result                    |
| --------------- | ------------------------- |
| `"environment"` | `{x: {b: 5}, y: 2}`       |
| `"merged"`      | `{x: {a: 1, b: 5}, y: 2}` |

### Switch to the `"merged"` interpolation scope

To select the `"merged"` scope, add it to `CONFIG_LOADER_ARGS`:

```python
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    "interpolation_scope": "merged",
}
```
