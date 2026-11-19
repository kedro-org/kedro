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

!!! tip "Recommended with `KedroServiceSession`"

    `LazyOmegaConfigLoader` is designed for long-lived processes such as `KedroServiceSession`. If you change how your project uses `KedroServiceSession` to rely on it, also set `CONFIG_LOADER_CLASS` in `settings.py`, as shown in [Configure the loader](#configure-the-loader). Projects that do not need it can keep the default.

!!! warning "Experimental"

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

The loader reads and caches the raw files for a key on first access, then
resolves them into a Python dictionary. Later accesses reuse the cached files
instead of reading them again. Unlike `OmegaConfigLoader`, the loader doesn't
pick up file changes on subsequent accesses. Call `preload()` or create a new
loader to read the files again. Ensure that the configured environment
directories exist, even if they contain no matching files.

## Preload and resolve per run

Use `preload()` before serving repeated requests. It reads and caches the
configured files in a snapshot. It also resolves globals and credentials. Key
access and `with_runtime_params()` reuse that snapshot even if files change on
disk; call `preload()` again to read the files anew.

!!! warning "`preload()` refreshes files, not your overrides"

    Calling `preload()` again re-reads every file, but it does not reset the loader. Values that you assigned yourself, such as `loader["globals"] = ...`, are kept and keep replacing the matching files. `preload()` logs, at `INFO` level, the keys whose values it keeps instead of reading them from files.

    To make `preload()` read a key from the files again, delete your override with `del loader[key]` and call `preload()`.

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

As with `OmegaConfigLoader`, the runtime parameters are also merged into `parameters`: `customer_id` appears in the result, and a runtime value replaces a YAML key with the same name. `KedroContext` reads runtime parameters from this result. The values stay available on the view as `first_run.runtime_params`.

Each `with_runtime_params()` call returns a per-run view with its own runtime parameters and explicit configuration overrides. The views share the loader's raw configuration snapshot. Resolving one view does not change the results of another.

!!! note

    The per-run view resolves configuration only. It does not create a `KedroContext`, catalog, or run a pipeline. Integration with `KedroServiceSession` is a separate step.

## Inspect unresolved configuration

Use `get_unresolved_config(key)` to inspect a read-only, merged `DictConfig`
without resolving its interpolations. For example, given these files:

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

## Configuration lifetime

The loader keeps its configuration snapshot until `preload()` is called again. Each `preload()` call re-reads the files and replaces the snapshot; if reading fails, the previous snapshot is kept. Changes to YAML files after preloading are not picked up by key access or by `with_runtime_params()`. Views created before a new `preload()` keep the snapshot they were created from.

Credentials are resolved as static configuration, not separately for each run. Pass values that change between runs through `with_runtime_params()` and the `runtime_params` resolver in parameters or catalog configuration.

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
