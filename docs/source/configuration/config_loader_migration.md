# Migration guide for config loaders
The `ConfigLoader` and `TemplatedConfigLoader` classes have been deprecated since Kedro `0.18.12` and will be removed in Kedro `0.19.0`. To ensure a smooth transition, we strongly recommend you adopt the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) as soon as possible.
This migration guide outlines the primary distinctions between the old loaders and the `OmegaConfigLoader`, providing step-by-step instructions on updating your code base to utilise the new class effectively.

## [`ConfigLoader`](/kedro.config.ConfigLoader) to [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader)

### 1. Install the Required Library
The [`OmegaConfigLoader`](advanced_configuration.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). In order to use it you need to ensure you have both a version of Kedro of `0.18.5` or above and `omegaconf` installed.
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
To use `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```diff
+ from kedro.config import OmegaConfigLoader  # new import

+ CONFIG_LOADER_CLASS = OmegaConfigLoader
```

### 3. Import Statements
Replace the import statement for `ConfigLoader` with the one for `OmegaConfigLoader`:

```diff
- from kedro.config import ConfigLoader

+ from kedro.config import OmegaConfigLoader
```

### 4. File Format Support
`OmegaConfigLoader` supports only `yaml` and `json` file formats. Make sure that all your configuration files are in one of these formats. If you previously used other formats with `ConfigLoader`, convert them to `yaml` or `json`.

### 5. Load Configuration
The method to load the configuration using `OmegaConfigLoader` differs slightly from that used by `ConfigLoader`, which allowed users to access configuration through the `.get()` method and required patterns as argument.
When you migrate to use `OmegaConfigLoader` it  requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

```diff
- conf_path = str(project_path / settings.CONF_SOURCE)
- conf_loader = ConfigLoader(conf_source=conf_path, env="local")
- catalog = conf_loader.get("catalog*")

+ conf_path = str(project_path / settings.CONF_SOURCE)
+ config_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
+ catalog = config_loader["catalog"]
```

In this example, `"catalog"` is the key to the default catalog patterns specified in the `OmegaConfigLoader` class.

### 6. Exception Handling
For error and exception handling, most errors are the same. Those you need to be aware of that are different between the original `ConfigLoader` and `OmegaConfigLoader` are as follows:
* `OmegaConfigLoader` throws a `MissingConfigException` when configuration paths don't exist, rather than the `ValueError` used in `ConfigLoader`.
* In `OmegaConfigLoader`, if there is bad syntax in your configuration files, it will trigger a `ParserError` instead of a `BadConfigException` used in `ConfigLoader`.

## [`TemplatedConfigLoader`](/kedro.config.TemplatedConfigLoader) to [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader)

### 1. Install the required library
The [`OmegaConfigLoader`](advanced_configuration.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). Features that replace `TemplatedConfigLoader` functionality have been released in later versions, so we recommend users
to install at least Kedro version `0.18.13` to properly replace the `TemplatedConfigLoader` with `OmegaConfigLoader`.
You can install both this Kedro version and `omegaconf` using `pip`:

```bash
pip install "kedro>=0.18.13, <0.19.0"
```
This would be the minimum required Kedro version which includes `omegaconf` as a dependency and the necessary functionality to replace `TemplatedConfigLoader`.
Or you can run:
```bash
pip install -U kedro
```

This command installs the most recent version of Kedro which also includes `omegaconf` as a dependency.

### 2. Use the `OmegaConfigLoader`
To use `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

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
`OmegaConfigLoader` supports only `yaml` and `json` file formats. Make sure that all your configuration files are in one of these formats. If you were using other formats with `TemplatedConfigLoader`, convert them to `yaml` or `json`.

### 5. Load configuration
The method to load the configuration using `OmegaConfigLoader` differs slightly from that used by `TemplatedConfigLoader`, which allowed users to access configuration through the `.get()` method and required patterns as argument.
When you migrate to use `OmegaConfigLoader` it  requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

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
Templating of values is done through native [variable interpolation in `OmegaConfigLoader`](advanced_configuration.md#how-to-do-templating-with-the-omegaconfigloader). Where in `TemplatedConfigLoader` it was necessary to
provide the template values in a `globals` file or dictionary, in `OmegaConfigLoader` you can provide these values within the same file that has the placeholders or a file that has a name that follows [the same config pattern specified](configuration_basics.md#configuration-patterns).
The variable interpolation is scoped to a specific configuration type and environment. If you want to share templated values across configuration types and environments, [you will need to use globals](#7-globals).

Suppose you are migrating a templated **catalog** file from using `TemplatedConfigLoader` to `OmegaConfigLoader` you would do the following:
1. Rename `conf/base/globals.yml` to match the patterns specified for catalog (`["catalog*", "catalog*/**", "**/catalog*"]`), for example `conf/base/catalog_globals.yml`
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

#### Providing default values for templates via `oc.select`
To provide a default for any template values you have to use [the omegaconf `oc.select` resolver](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#oc-select).

```diff
boats:
  users:
    - fred
-    - "${write_only_user|ron}"
+    - "${oc.select:write_only_user,ron}"
```

### 7. Globals
If you want to share variables across configuration types, for example parameters and catalog, and environments you need to use [the custom globals resolver with the `OmegaConfigLoader`](advanced_configuration.md#how-to-use-global-variables-with-the-omegaconfigloader).
The `OmegaConfigLoader` requires global values to be provided in a `globals.yml` file. Note that using a `globals_dict` to provide globals is not supported with `OmegaConfigLoader`. The following section explains the differences between using globals with `TemplatedConfigLoader` and the `OmegaConfigLoader`.

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

You no longer need to set `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md) to find this `globals.yml` file, because the
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

### 8. Deprecation of Jinja2
`OmegaConfigLoader` does not support Jinja2 syntax in configuration. However, users can achieve similar functionality with the `OmegaConfigLoader` in combination with [dataset factories](../data/kedro_dataset_factories.md).
If you take the example from [the `TemplatedConfigLoader` with Jinja2 documentation](advanced_configuration.md#how-to-use-jinja2-syntax-in-configuration) you can rewrite your configuration as follows to work with `OmegaConfigLoader`:

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
* For missing template values `OmegaConfigLoader` throws `omegaconf.errors.InterpolationKeyError`.
