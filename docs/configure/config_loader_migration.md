# Migration guide for config loaders

The `ConfigLoader` and `TemplatedConfigLoader` classes have been deprecated since Kedro `0.18.12` and were removed in Kedro `0.19.0`. To use that release or later, you must adopt the [kedro.config.OmegaConfigLoader][].
This guide covers those migrations and the optional switch from
`OmegaConfigLoader` to the experimental `LazyOmegaConfigLoader`.

## On this page

- [`ConfigLoader` to `OmegaConfigLoader`](#configloader-to-omegaconfigloader)
- [`TemplatedConfigLoader` to `OmegaConfigLoader`](#templatedconfigloader-to-omegaconfigloader)
- [`OmegaConfigLoader` to `LazyOmegaConfigLoader`](#omegaconfigloader-to-lazyomegaconfigloader)

## `ConfigLoader` to `OmegaConfigLoader`

### 1. Install the required library

The [`OmegaConfigLoader`](configuration_basics.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). To use it you need Kedro (version `0.18.5` or later) and `omegaconf` installed.
You can install both using `pip`:

```bash
pip install kedro==0.18.5
```

This would be the minimum required Kedro version which includes `omegaconf` as a dependency.
Or you can run:

```bash
pip install -U kedro
```

This command installs the most recent version of Kedro which also includes `omegaconf` as a dependency.

### 2. Use the `OmegaConfigLoader`

To use `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../tutorials/settings.md):

```diff
+ from kedro.config import OmegaConfigLoader  # new import

+ CONFIG_LOADER_CLASS = OmegaConfigLoader
```

### 3. Import statements

Replace the import statement for `ConfigLoader` with the one for `OmegaConfigLoader`:

```diff
- from kedro.config import ConfigLoader

+ from kedro.config import OmegaConfigLoader
```

### 4. File format support

`OmegaConfigLoader` supports `yaml` and `json` file formats. Make sure that all your configuration files use one of these formats. If you relied on other formats with `ConfigLoader`, convert them to `yaml` or `json`.

### 5. Load configuration

The method to load the configuration using `OmegaConfigLoader` differs slightly from that used by `ConfigLoader`, which allowed users to access configuration through the `.get()` method and required patterns as argument.
When you migrate to use `OmegaConfigLoader`, it requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](how_to_configure_project.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

```diff
- conf_path = str(project_path / settings.CONF_SOURCE)
- conf_loader = ConfigLoader(conf_source=conf_path, env="local")
- catalog = conf_loader.get("catalog*")

+ conf_path = str(project_path / settings.CONF_SOURCE)
+ config_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
+ catalog = config_loader["catalog"]
```

In this example, `"catalog"` is the key to the default catalog patterns specified in the `OmegaConfigLoader` class.

### 6. Exception handling

For error and exception handling, most errors are the same. Those you need to be aware of that are different between the original `ConfigLoader` and `OmegaConfigLoader` are as follows:

- `OmegaConfigLoader` throws a `MissingConfigException` when configuration paths don't exist, rather than the `ValueError` used in `ConfigLoader`.
- In `OmegaConfigLoader`, if there is bad syntax in your configuration files, it will trigger a `ParserError` instead of a `BadConfigException` used in `ConfigLoader`.

## `TemplatedConfigLoader` to `OmegaConfigLoader`

### 1. Install the required library

The [`OmegaConfigLoader`](configuration_basics.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). Features that replace `TemplatedConfigLoader` functionality have been released in later versions, so we recommend users
install Kedro version `0.18.13` or later to properly replace the `TemplatedConfigLoader` with `OmegaConfigLoader`.
You can install both this Kedro version and `omegaconf` using `pip`:

```bash
pip install "kedro>=0.18.13"
```

This would be the minimum required Kedro version which includes `omegaconf` as a dependency and the necessary functionality to replace `TemplatedConfigLoader`.
Or you can run:

```bash
pip install -U kedro
```

This command installs the most recent version of Kedro which also includes `omegaconf` as a dependency.

### 2. Use the `OmegaConfigLoader`

To use `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../tutorials/settings.md):

```diff
+ from kedro.config import OmegaConfigLoader  # new import

+ CONFIG_LOADER_CLASS = OmegaConfigLoader
```

### 3. Import statements

Replace the import statement for `TemplatedConfigLoader` with the one for `OmegaConfigLoader`:

```diff
- from kedro.config import TemplatedConfigLoader
+ from kedro.config import OmegaConfigLoader
```

### 4. File format support

`OmegaConfigLoader` supports `yaml` and `json` file formats. Make sure that all your configuration files use one of these formats. If you used other formats with `TemplatedConfigLoader`, convert them to `yaml` or `json`.

### 5. Load configuration

The method to load the configuration using `OmegaConfigLoader` differs slightly from that used by `TemplatedConfigLoader`, which allowed users to access configuration through the `.get()` method and required patterns as argument.
When you migrate to use `OmegaConfigLoader`, it requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](how_to_configure_project.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

```diff
- conf_path = str(project_path / settings.CONF_SOURCE)
- conf_loader = TemplatedConfigLoader(conf_source=conf_path, env="local")
- catalog = conf_loader.get("catalog*")

+ conf_path = str(project_path / settings.CONF_SOURCE)
+ config_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
+ catalog = config_loader["catalog"] # note the key accessor syntax
```

In this example, the `"catalog"` key points to the default catalog patterns specified in the `OmegaConfigLoader` class.

### 6. Templating of values

Templating of values is done through native [variable interpolation in `OmegaConfigLoader`](how_to_use_templating.md#how-to-template-catalog-files). With `TemplatedConfigLoader` you had to provide the template values in a `globals` file or dictionary. `OmegaConfigLoader` lets you keep these values within the same file that has the placeholders or in a file whose name follows [the same config pattern specified](configuration_basics.md#configuration-patterns).
The variable interpolation is scoped to a specific configuration type and environment. If you want to share templated values across configuration types and environments, [you will need to use globals](#7-globals).

Suppose you are migrating a templated **catalog** file from using `TemplatedConfigLoader` to `OmegaConfigLoader` you would do the following:

1. Rename `conf/base/globals.yml` to match the patterns specified for catalog (`["catalog*", "catalog*/**", "**/catalog*"]`), for example `conf/base/catalog_variables.yml`

2. Add an underscore `_` to any catalog template values. This is needed because of how catalog entries are validated.

    ```diff
    - bucket_name: "my_s3_bucket"
    + _bucket_name: "my_s3_bucket" # kedro requires `_` to mark templatable keys
    - key_prefix: "my/key/prefix/"
    + _key_prefix: "my/key/prefix/"

    - datasets:
    + _datasets:
        csv: "pandas.CSVDataset"
        spark: "spark.SparkDataset"

    ```

3. Update `catalog.yml` with the underscores `_` at the beginning of the templated value names.

    ```diff
    raw_boat_data:
    -   type: "${datasets.spark}"
    +   type: "${_datasets.spark}"
    -   filepath: "s3a://${bucket_name}/${key_prefix}/raw/boats.csv"
    +   filepath: "s3a://${_bucket_name}/${_key_prefix}/raw/boats.csv"
        file_format: parquet

    raw_car_data:
    -    type: "${datasets.csv}"
    +    type: "${_datasets.csv}"
    -    filepath: "s3://${bucket_name}/data/${key_prefix}/raw/cars.csv"
    +    filepath: "s3://${_bucket_name}/data/${_key_prefix}/raw/cars.csv"
    ```

#### Providing default values for templates with `oc.select`

To provide a default for any template values you have to use [the OmegaConf `oc.select` resolver](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#oc-select).

```diff
boats:
  users:
    - fred
-    - "${write_only_user|ron}"
+    - "${oc.select:write_only_user,ron}"
```

### 7. Globals

If you want to share variables across configuration types (for example parameters and catalog) and environments, use [the custom globals resolver with the `OmegaConfigLoader`](how_to_use_templating.md#how-to-use-global-variables-with-the-omegaconfigloader).
The `OmegaConfigLoader` requires global values to be provided in a `globals.yml` file.
Using a `globals_dict` to provide globals is not supported with `OmegaConfigLoader`. The following section explains the differences between using globals with `TemplatedConfigLoader` and the `OmegaConfigLoader`.

Let's assume your project contains a `conf/base/globals.yml` file with the following contents:

```yaml
bucket_name: "my_s3_bucket"
key_prefix: "my/key/prefix/"

datasets:
    csv: "pandas.CSVDataset"
    spark: "spark.SparkDataset"

folders:
    raw: "01_raw"
    int: "02_intermediate"
    pri: "03_primary"
    fea: "04_feature"
```

You no longer need to set `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../tutorials/settings.md) to find this `globals.yml` file, because the
`OmegaConfigLoader` is configured to pick up files named `globals.yml` by default.

```diff
- CONFIG_LOADER_ARGS = {"globals_pattern": "*globals.yml"}
```

The globals templating in your catalog configuration will need to be updated to use the globals resolver as follows:

```diff
raw_boat_data:
-   type: "${datasets.spark}"
+   type: "${globals:datasets.spark}"  # nested paths into global dict are allowed
-   filepath: "s3a://${bucket_name}/${key_prefix}/${folders.raw}/boats.csv"
+   filepath: "s3a://${globals:bucket_name}/${globals:key_prefix}/${globals:folders.raw}/boats.csv"
    file_format: parquet

raw_car_data:
-   type: "${datasets.csv}"
+   type: "${globals:datasets.csv}"
-   filepath: "s3://${bucket_name}/data/${key_prefix}/${folders.raw}/${filename|cars.csv}"  # default to 'cars.csv' if the 'filename' key is not found in the global dict
+   filepath: "s3://${globals:bucket_name}/data/${globals:key_prefix}/${globals:folders.raw}/${globals:filename,'cars.csv'}"  # default to 'cars.csv' if the 'filename' key is not found in the global dict
```

### 8. Deprecation of Jinja2 support

`OmegaConfigLoader` does not support Jinja2 syntax in configuration. You can achieve similar functionality with the `OmegaConfigLoader` in combination with [dataset factories](../catalog-data/kedro_dataset_factories.md).
The following example shows how you can rewrite your Jinja2 configuration to work with `OmegaConfigLoader`:

```diff
# catalog.yml
- {% for speed in ['fast', 'slow'] %}
- {{ speed }}-trains:
+ "{speed}-trains":
    type: MemoryDataset

- {{ speed }}-cars:
+ "{speed}-cars":
    type: pandas.CSVDataset
-    filepath: s3://${bucket_name}/{{ speed }}-cars.csv
+    filepath: s3://${bucket_name}/{speed}-cars.csv
    save_args:
        index: true

- {% endfor %}
```

### 9. Exception handling

For error and exception handling, most errors are the same. Those you need to be aware of that are different between the original `TemplatedConfigLoader` and `OmegaConfigLoader` are as follows:

- For missing template values `OmegaConfigLoader` throws `omegaconf.errors.InterpolationKeyError`.

## `OmegaConfigLoader` to `LazyOmegaConfigLoader`

Migration is optional: `OmegaConfigLoader` remains the default.
`LazyOmegaConfigLoader` is experimental and emits a warning on first
instantiation. See [Caching configuration](caching_configuration.md)
before deciding whether your project benefits from it.

### 1. Opt in through project settings

Set the loader in `src/<package_name>/settings.py`:

```python
from kedro.config import LazyOmegaConfigLoader

CONFIG_LOADER_CLASS = LazyOmegaConfigLoader
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
}
```

Keep your existing loader arguments and leave `interpolation_scope` at its
default, `"environment"`. Existing YAML, key access, and CLI commands such
as `kedro run --params` need no changes for ordinary single-run usage.
A new loader reads the files for each CLI run.

This isn't complete behavioural parity. Review the changes below if
plugins, Hooks, or notebooks use the loader directly.

### 2. Refresh cached files explicitly

If code edits files and then reads the same key from the same loader,
refresh the snapshot first:

```python
parameters = loader["parameters"]
# Edit the parameter files.
loader.preload()
updated_parameters = loader["parameters"]
```

Alternatively, construct a new loader. `preload()` keeps explicit
overrides, such as `loader["parameters"] = {...}`. Delete an override
before preloading if the files should supply that key again.

### 3. Create a view for each set of runtime parameters

For repeated resolutions, reuse the files rather than constructing a new
loader for each run:

```python
loader.preload()
for customer_id in ("customer-001", "customer-002"):
    view = loader.with_runtime_params({"customer_id": customer_id})
    parameters = view["parameters"]
```

Constructor-time `runtime_params` still work. The new method is useful
when reusing a snapshot; it isn't required for ordinary CLI usage.
Don't mutate a shared loader's runtime parameters during concurrent
resolutions. Use per-run views instead.

### 4. Check error handling and dictionary updates

Globals errors now surface on first configuration access or `preload()`,
rather than during construction. Move error handling around those calls
if it previously guarded only the constructor. Preloading validates file
syntax and duplicate keys, but doesn't resolve catalog or parameter
interpolations.

The lazy loader returns copies of explicitly assigned dictionaries.
Don't rely on mutating a returned dictionary to update the loader:

```python
parameters = loader["parameters"]
parameters["learning_rate"] = 0.2
loader["parameters"] = parameters
```

This assignment creates an explicit override, not a file update.
Use [`get_unresolved_config()`](how_to_cache_configuration.md#inspect-unresolved-configuration)
to inspect raw configuration. Its result is a read-only copy.

### 5. Check custom loaders and resolver usage

The lazy loader subclasses `OmegaConfigLoader`, but doesn't call its
constructor. It also uses separate cached read and resolution paths.
Review custom subclasses that override private loading methods before
switching their base class.

Configure custom resolvers through `custom_resolvers`. Don't rely on
constructing a loader to register `globals`, `runtime_params`, or
`oc.env` for unrelated OmegaConf operations.

The lazy loader restricts `oc.env` to credentials by default, even if
another caller registers it globally. Explicitly configure it if other
configuration requires it, following the
[custom resolver guidance](how_to_use_templating.md#how-to-use-resolvers-in-the-omegaconfigloader).
Mixing direct OmegaConf operations or non-lazy loaders with concurrent
lazy resolutions can still interfere with the global resolver registry.

Keep the default interpolation scope when migrating. Review the
[scope examples and performance trade-offs](how_to_cache_configuration.md#interpolation-scope)
before selecting `"merged"`, which can change resolved values.
