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

### 1. Install the Required Library
The [`OmegaConfigLoader`](advanced_configuration.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). Features that replace `TemplatedConfigLoader` functionality have been released in later versions, so we recommend users
to install at least Kedro version `0.18.X` to properly replace the `TemplatedConfigLoader` with `OmegaConfigLoader`.
You can install both this Kedro version and `omegaconf` using `pip`:

```bash
pip install kedro==0.18.X
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

### 3. Import Statements
Replace the import statement for `TemplatedConfigLoader` with the one for `OmegaConfigLoader`:

```diff
- from kedro.config import TemplatedConfigLoader

+ from kedro.config import OmegaConfigLoader
```

### 4. File Format Support
`OmegaConfigLoader` supports only `yaml` and `json` file formats. Make sure that all your configuration files are in one of these formats. If you were using other formats with `TemplatedConfigLoader`, convert them to `yaml` or `json`.

### 5. Load Configuration
The method to load the configuration using `OmegaConfigLoader` differs slightly from that used by `TemplatedConfigLoader`, which allowed users to access configuration through the `.get()` method and required patterns as argument.
When you migrate to use `OmegaConfigLoader` it  requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

```diff
- conf_path = str(project_path / settings.CONF_SOURCE)
- conf_loader = TemplatedConfigLoader(conf_source=conf_path, env="local")
- catalog = conf_loader.get("catalog*")

+ conf_path = str(project_path / settings.CONF_SOURCE)
+ config_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
+ catalog = config_loader["catalog"]
```

In this example, `"catalog"` is the key to the default catalog patterns specified in the `OmegaConfigLoader` class.

### 6. Templating of Values
Templating of values is done through [variable interpolation in `OmegaConfigLoader`](advanced_configuration.md#how-to-do-templating-with-the-omegaconfigloader). Where in `TemplatedConfigLoader` it was necessary to
provide the template values in a `globals` file or dictionary, in `OmegaConfigLoader` you can provide these values within the same file that has the placeholders or a file that has a name that follows [the same config pattern specified](configuration_basics.md#configuration-patterns).

Suppose you are migrating a templated **catalog** file from using `TemplatedConfigLoader` to `OmegaConfigLoader` you would do the following:
1. Rename `conf/base/globals.yml` to match the patterns specified for catalog (`["catalog*", "catalog*/**", "**/catalog*"]`), e.g. `conf/base/catalog_globals.yml`
2. Add an underscore `_` to any catalog template values. This is needed because of how catalog entries are validated.

```diff
- bucket_name: "my_s3_bucket"
+ _bucket_name: "my_s3_bucket"
- key_prefix: "my/key/prefix/"
+ _key_prefix: "my/key/prefix/"

- datasets:
+ _datasets:
    csv: "pandas.CSVDataSet"
    spark: "spark.SparkDataSet"

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
To provide a default for any template values you have to use [the omegaconf `oc.select` resolver](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#oc-select).

```diff
boats:
  users:
    - fred
-    - "${write_only_user|ron}"
+    - "${oc.select:write_only_user,ron}"
```

### 7. Globals
* Globals for OCL:
   * 1. within the same config params and catalog (add underscore for catalog)
   * 2. between config
   * Only globals through file not through dict
   * Mix of config level and between config ?

### 8. Jinja2
`OmegaConfigLoader` does not support Jinja2 syntax in configuration. However, users can achieve similar functionality with the `OmegaConfigLoader` in combination with [dataset factories](../data/data_catalog.md#load-multiple-datasets-with-similar-configuration-using-dataset-factories).
If you take the example from [the `TemplatedConfigLoader` with Jinja2 documentation](advanced_configuration.md#how-to-use-jinja2-syntax-in-configuration) you can rewrite your configuration as follows to work with `OmegaConfigLoader`:

```diff
# catalog.yml
- {% for speed in ['fast', 'slow'] %}
- {{ speed }}-trains:
+ "{speed}-trains":
    type: MemoryDataSet

- {{ speed }}-cars:
+ "{speed}-cars":
    type: pandas.CSVDataSet
-    filepath: s3://${bucket_name}/{{ speed }}-cars.csv
+    filepath: s3://${bucket_name}/{speed}-cars.csv
    save_args:
        index: true

- {% endfor %}
```

### 9. Exception Handling
For error and exception handling, most errors are the same. Those you need to be aware of that are different between the original `TemplatedConfigLoader` and `OmegaConfigLoader` are as follows:
* For missing template values `OmegaConfigLoader` throws `omegaconf.errors.InterpolationKeyError`.
