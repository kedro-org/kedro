# Use the `LazyOmegaConfigLoader`

This guide shows how to opt in to `LazyOmegaConfigLoader`, preload configuration, and resolve it with different runtime parameters. It assumes that you are familiar with [Kedro configuration](configuration_basics.md).

`LazyOmegaConfigLoader` is an opt-in alternative to `OmegaConfigLoader`, which remains the default `CONFIG_LOADER_CLASS`. It caches the raw configuration files so that the same configuration can be resolved repeatedly with different runtime parameters.

!!! tip "Recommended with `KedroServiceSession`"

    `LazyOmegaConfigLoader` is designed for long-lived processes such as `KedroServiceSession`. If you change how your project uses `KedroServiceSession` to rely on it, also set `CONFIG_LOADER_CLASS` in `settings.py`, as shown in [Configure the loader](#configure-the-loader). Projects that do not need it can keep the default.

!!! warning "Experimental methods"

    The loader itself is not experimental, but these public methods are and may change in a future Kedro release: `preload()`, `with_runtime_params()` and `get_unresolved_config()`. Using them emits a `KedroExperimentalWarning`; reading keys such as `loader["parameters"]` does not.

By default, the loader resolves interpolations like `OmegaConfigLoader` does. To resolve them after merging the environments instead, [switch to the `"merged"` interpolation scope](#switch-to-the-merged-interpolation-scope).

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

It adds `interpolation_scope`, which controls when interpolation is resolved:

| Value           | Behaviour                                                                           |
| --------------- | ----------------------------------------------------------------------------------- |
| `"environment"` | Resolve each environment before merging, matching `OmegaConfigLoader`. The default. |
| `"merged"`      | Merge the raw configuration from the environments, then resolve interpolations.     |

### Switch to the `"merged"` interpolation scope

Add `interpolation_scope` to `CONFIG_LOADER_ARGS`:

```python
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    "interpolation_scope": "merged",
}
```

This can produce different results from `OmegaConfigLoader`. See [Interpolation scope](#interpolation-scope) before choosing it.

## Preload and resolve per run

Use `preload()` before serving repeated requests. It reads and merges the configured files into a snapshot. Key access and `with_runtime_params()` reuse that snapshot even if files change on disk; call `preload()` again to read the files anew.

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

`__getitem__` returns a resolved Python dictionary, as it does with `OmegaConfigLoader`. The experimental `get_unresolved_config(key)` method returns the read-only, merged `DictConfig` for a key without resolving its interpolations.

!!! note

    The per-run view resolves configuration only. It does not create a `KedroContext`, catalog, or run a pipeline. Integration with `KedroServiceSession` is a separate step.

## Interpolation scope

Lazy resolution and environment merge order are independent. `"environment"`, the default, preserves existing results; `"merged"` resolves interpolations against the combined environments.

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

`OmegaConfigLoader` and `LazyOmegaConfigLoader(interpolation_scope="environment")` return `param1: "base"`. `LazyOmegaConfigLoader(interpolation_scope="merged")` returns `param1: "local"`.

Both scopes merge `runtime_params` into `parameters`. The `"merged"` scope does so after merging environments, which can preserve base keys that the default destructive strategy replaces in `OmegaConfigLoader`.

For example, with `x: {a: 1}` in `conf/base/parameters.yml`, `y: 2` in `conf/local/parameters.yml`, and runtime parameters `{"x": {"b": 5}}`, the results differ:

| Scope           | Result                    |
| --------------- | ------------------------- |
| `"environment"` | `{x: {b: 5}, y: 2}`       |
| `"merged"`      | `{x: {a: 1, b: 5}, y: 2}` |

## Configuration lifetime

The loader keeps its configuration snapshot until `preload()` is called again. Each `preload()` call re-reads the files and replaces the snapshot; if reading fails, the previous snapshot is kept. Changes to YAML files after preloading are not picked up by key access or by `with_runtime_params()`. Views created before a new `preload()` keep the snapshot they were created from.

Credentials are resolved as static configuration, not separately for each run. Pass values that change between runs through `with_runtime_params()` and the `runtime_params` resolver in parameters or catalog configuration.
