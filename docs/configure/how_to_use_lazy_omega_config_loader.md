# Use the experimental `LazyOmegaConfigLoader`

This guide shows how to opt in to `LazyOmegaConfigLoader`, preload configuration, and resolve it with different runtime parameters. It assumes that you are familiar with [Kedro configuration](configuration_basics.md).

!!! warning "Experimental"

    `LazyOmegaConfigLoader` is experimental and may change in a future Kedro release. Its default interpolation scope, `"merged"`, can produce different results from `OmegaConfigLoader`.

## Configure the loader

Set `CONFIG_LOADER_CLASS` in your project's `src/<package_name>/settings.py`:

```python
from kedro.config import LazyOmegaConfigLoader

CONFIG_LOADER_CLASS = LazyOmegaConfigLoader
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    "interpolation_scope": "merged",
}
```

`LazyOmegaConfigLoader` accepts the same file patterns, merge strategies, custom resolvers, and runtime-parameter type-selection option as `OmegaConfigLoader`. It adds `interpolation_scope`, which controls when interpolation is resolved:

| Value           | Behaviour                                                                                            |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| `"merged"`      | Merge the raw configuration from the environments, then resolve interpolations. This is the default. |
| `"environment"` | Resolve each environment before merging, matching `OmegaConfigLoader`.                               |

See [Interpolation scope](#interpolation-scope) before choosing a value.

## Preload and resolve per run

Use `preload()` before serving repeated requests. It reads the configured raw files once, so later calls reuse the snapshot even if files change on disk.

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
    interpolation_scope="merged",
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

`__getitem__` returns a resolved Python dictionary, as it does with `OmegaConfigLoader`. `_get_unresolved_config(key)` is a private method used to inspect the read-only, merged `DictConfig`; it is not a supported public API.

!!! note

    The per-run view resolves configuration only. It does not create a `KedroContext`, catalog, or run a pipeline. Integration with `KedroServiceSession` is a separate step.

## Interpolation scope

Lazy resolution and environment merge order are independent. `"environment"` preserves existing results; `"merged"` resolves interpolations against the combined environments.

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

The loader keeps its raw configuration snapshot for its lifetime. `preload()` makes file and parse work happen before repeated run-time resolution. Changes to YAML files after preloading are not picked up; create a new loader to read an updated configuration.

Credentials are resolved as static configuration, not separately for each run. Pass values that change between runs through `with_runtime_params()` and the `runtime_params` resolver in parameters or catalog configuration.
