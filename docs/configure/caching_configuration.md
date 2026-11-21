# Caching configuration

Caching configuration separates reading files from resolving their values.
`LazyOmegaConfigLoader` reads and caches configuration files, then resolves
their contents with different runtime parameters. This avoids reading and
parsing the same files for each run. It's useful in long-lived applications,
such as services or applications that use a loader directly with Streamlit
or FastAPI.

`LazyOmegaConfigLoader` is an opt-in alternative to `OmegaConfigLoader`,
which remains the default configuration loader.

!!! warning "Experimental"

    The class and its public methods are experimental and may change or be
    removed in a future release. Instantiating it emits a
    `KedroExperimentalWarning` once per process.

## Reading and resolving

Reading discovers configuration files and parses their contents. Resolving
evaluates interpolations such as `${runtime_params:customer_id}` and returns
a Python dictionary.

`OmegaConfigLoader` repeats file discovery, reading, parsing, and resolution
on each key access. `LazyOmegaConfigLoader` caches the parsed configuration
for a key on first access. Later accesses reuse it while resolving values.
The cache stores raw configuration, not a single result shared by every run.

This suits repeated access with changing runtime parameters. For a single
CLI run, cache setup adds overhead without the same opportunity for reuse.
Keep `OmegaConfigLoader` if you don't need caching.

## Configuration cache

Edits on disk don't affect later reads of a cached key.
`preload()` reads the configured files before requests
start, avoiding different keys first reading files at different times.

Calling `preload()` again replaces the cache if loading succeeds.
Existing per-run views keep using the previous cache. Explicit overrides
assigned to the loader remain in place.

The loader resolves globals when first needed and caches the result.
`preload()` also resolves and caches credentials, so credentials don't vary
between its per-run views.
Neither globals nor preloaded credentials are intended for per-run values.

## Repeated runs

`with_runtime_params()` creates a per-run view that shares the raw configuration cache
but has its own runtime parameters and resolver state. Each view returns
configuration resolved for that run without reading the same files again.

The view resolves configuration; it doesn't create a context, a data catalog,
or a pipeline run. Framework integration is a separate step.

## Thread safety and resolver isolation

OmegaConf's resolver registry is process-global. The lazy loader uses a
shared lock when reading or resolving configuration to protect its resolver
operations. Per-run views keep separate runtime-parameter state.

The lock protects runtime-parameter resolver operations during concurrent
lazy-loader resolutions. It doesn't make arbitrary OmegaConf usage thread-safe.
Code using `OmegaConfigLoader` directly, or registering resolvers outside the
lock, can still interfere.

Custom resolvers other than `globals`, `runtime_params`, and `oc.env` are
registered process-wide during loader construction, outside the lock. Even
when all loaders are created before runs start, their custom resolvers aren't
isolated: if a name is already registered, a later loader skips its resolver
unless it specifies `replace=True`. Replacing a resolver can affect other
loaders. Use distinct resolver names or share the same implementation.

For example, consider this `conf/base/parameters.yml`:

```yaml
message: ${example_greeting:}
```

In a process without an existing `example_greeting` resolver:

```python
from kedro.config import LazyOmegaConfigLoader

a = LazyOmegaConfigLoader(
    "conf", base_env="base", default_run_env="base",
    custom_resolvers={"example_greeting": lambda: "Hello"},
)
b = LazyOmegaConfigLoader(
    "conf", base_env="base", default_run_env="base",
    custom_resolvers={"example_greeting": lambda: "Bonjour"},
)

print(b["parameters"]["message"])  # Hello: B's resolver was silently skipped
```

If B instead registers its resolver with `replace=True`, A's later
resolutions can use B's resolver:

```python
b = LazyOmegaConfigLoader(
    "conf",
    base_env="base",
    default_run_env="base",
    custom_resolvers={"example_greeting": (lambda: "Bonjour", {"replace": True})},
)
print(a["parameters"]["message"])  # Bonjour
```

!!! warning "Avoid changing resolvers directly during runs"

    Changing the global resolver registry during a run can cause an ongoing
    resolution to use a different resolver or fail. For example, a Hook or
    node could register, replace, or remove a resolver through OmegaConf
    outside the loader's lock. Strongly avoid these changes during runs;
    configure resolvers before starting concurrent work instead.

The lock covers custom resolver execution, so slow resolvers can serialise
requests.

Don't mutate a shared loader's settings, overrides, or runtime parameters
while requests are resolving. Create separate per-run views instead.

By default, the lazy loader restricts `oc.env` to credentials. It temporarily
selects the configured resolver during its own operations, then restores the
previous global `oc.env` resolver.

## Further reading

- [How to cache configuration](how_to_cache_configuration.md)
- [Migrate from `OmegaConfigLoader`](config_loader_migration.md#omegaconfigloader-to-lazyomegaconfigloader)
