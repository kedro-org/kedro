# Advanced configuration
The documentation on [configuration](./configuration_basics.md) describes how to satisfy most common requirements of standard Kedro project configuration:

By default, Kedro is set up to use the [ConfigLoader](/kedro.config.ConfigLoader) class. Kedro also provides two additional configuration loaders with more advanced functionality: the [TemplatedConfigLoader](/kedro.config.TemplatedConfigLoader) and the [OmegaConfigLoader](/kedro.config.OmegaConfigLoader).
Each of these classes are alternatives for the default `ConfigLoader` and have different features. The following sections describe each of these classes and their specific functionality in more detail.

This page also contains a set of guidance for advanced configuration requirements of standard Kedro projects:

* [How to change which configuration files are loaded](#how-to-change-which-configuration-files-are-loaded)
* [How to ensure non default configuration files get loaded](#how-to-ensure-non-default-configuration-files-get-loaded)
* [How to bypass the configuration loading rules](#how-to-bypass-the-configuration-loading-rules)
* [How to use Jinja2 syntax in configuration](#how-to-use-jinja2-syntax-in-configuration)
* [How to do templating with the `OmegaConfigLoader`](#how-to-do-templating-with-the-omegaconfigloader)
* [How to use global variables with the `OmegaConfigLoader`](#how-to-use-global-variables-with-the-omegaconfigloader)
* [How to override configuration with runtime parameters with the `OmegaConfigLoader`](#how-to-override-configuration-with-runtime-parameters-with-the-omegaconfigloader)
* [How to use resolvers in the `OmegaConfigLoader`](#how-to-use-resolvers-in-the-omegaconfigloader)
* [How to load credentials through environment variables with `OmegaConfigLoader`](#how-to-load-credentials-through-environment-variables)

## OmegaConfigLoader

[OmegaConf](https://omegaconf.readthedocs.io/) is a Python library designed to handle and manage settings. It serves as a YAML-based hierarchical system to organise configurations, which can be structured to accommodate various sources, allowing you to merge settings from multiple locations.

From Kedro 0.18.5 you can use the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) which uses `OmegaConf` to load data.

```{note}
`OmegaConfigLoader` is under active development. It is available from Kedro version 0.18.5 with additional features due in later releases. Let us know if you have any feedback about the `OmegaConfigLoader` by joining the [Kedro community on Slack](https://slack.kedro.org/).
```

`OmegaConfigLoader` can load `YAML` and `JSON` files. Acceptable file extensions are `.yml`, `.yaml`, and `.json`. By default, any configuration files used by the config loaders in Kedro are `.yml` files.

To use `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```python
from kedro.config import OmegaConfigLoader  # new import

CONFIG_LOADER_CLASS = OmegaConfigLoader
```

## TemplatedConfigLoader

```{warning}
`ConfigLoader` and `TemplatedConfigLoader` have been deprecated since Kedro `0.18.12` and will be removed in Kedro `0.19.0`. Refer to the [migration guide for config loaders](./config_loader_migration.md) for instructions on how to update your code to use `OmegaConfigLoader`.
```

Kedro provides an extension [TemplatedConfigLoader](/kedro.config.TemplatedConfigLoader) class that allows you to template values in configuration files. To apply templating in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```python
from kedro.config import TemplatedConfigLoader  # new import

CONFIG_LOADER_CLASS = TemplatedConfigLoader
```

### Provide template values through globals
When using the `TemplatedConfigLoader` you can provide values in the configuration template through a `globals` file or dictionary.

Let's assume the project contains a `conf/base/globals.yml` file with the following contents:

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

To point your `TemplatedConfigLoader` to the globals file, add it to the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```python
CONFIG_LOADER_ARGS = {"globals_pattern": "*globals.yml"}
```

Now the templating can be applied to the configuration. Here is an example of a templated `conf/base/catalog.yml` file:

```yaml
raw_boat_data:
    type: "${datasets.spark}"  # nested paths into global dict are allowed
    filepath: "s3a://${bucket_name}/${key_prefix}/${folders.raw}/boats.csv"
    file_format: parquet

raw_car_data:
    type: "${datasets.csv}"
    filepath: "s3://${bucket_name}/data/${key_prefix}/${folders.raw}/${filename|cars.csv}"  # default to 'cars.csv' if the 'filename' key is not found in the global dict
```

Under the hood, `TemplatedConfigLoader` uses [`JMESPath` syntax](https://github.com/jmespath/jmespath.py) to extract elements from the globals dictionary.


Alternatively, you can declare which values to fill in the template through a dictionary. This dictionary could look like the following:

```python
{
    "bucket_name": "another_bucket_name",
    "non_string_key": 10,
    "key_prefix": "my/key/prefix",
    "datasets": {"csv": "pandas.CSVDataset", "spark": "spark.SparkDataset"},
    "folders": {
        "raw": "01_raw",
        "int": "02_intermediate",
        "pri": "03_primary",
        "fea": "04_feature",
    },
}
```

To point your `TemplatedConfigLoader` to the globals dictionary, add it to the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```python
CONFIG_LOADER_ARGS = {
    "globals_dict": {
        "bucket_name": "another_bucket_name",
        "non_string_key": 10,
        "key_prefix": "my/key/prefix",
        "datasets": {"csv": "pandas.CSVDataset", "spark": "spark.SparkDataset"},
        "folders": {
            "raw": "01_raw",
            "int": "02_intermediate",
            "pri": "03_primary",
            "fea": "04_feature",
        },
    }
}
```

If you specify both `globals_pattern` and `globals_dict` in `CONFIG_LOADER_ARGS`, the contents of the dictionary resulting from `globals_pattern` are merged with the `globals_dict` dictionary. In case of conflicts, the keys from the `globals_dict` dictionary take precedence.


## Advanced Kedro configuration

### How to change which configuration files are loaded
If you want to change the patterns that the configuration loader uses to find the files to load you need to set the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md).
For example, if your `parameters` files are using a `params` naming convention instead of `parameters` (e.g. `params.yml`) you need to update `CONFIG_LOADER_ARGS` as follows:

```python
CONFIG_LOADER_ARGS = {
    "config_patterns": {
        "parameters": ["params*", "params*/**", "**/params*"],
    }
}
```

By changing this setting, the default behaviour for loading parameters will be replaced, while the other configuration patterns will remain in their default state.

### How to ensure non default configuration files get loaded
You can add configuration patterns to match files other than `parameters`, `credentials`, and `catalog` by setting the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md).
For example, if you want to load Spark configuration files you need to update `CONFIG_LOADER_ARGS` as follows:

```python
CONFIG_LOADER_ARGS = {
    "config_patterns": {
        "spark": ["spark*/"],
    }
}
```

### How to bypass the configuration loading rules
You can bypass the configuration patterns and set configuration directly on the instance of a config loader class. You can bypass the default configuration (catalog, parameters and credentials) as well as additional configuration.

```{code-block} python
:lineno-start: 10
:emphasize-lines: 8

from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path)

# Bypass configuration patterns by setting the key and values directly on the config loader instance.
conf_loader["catalog"] = {"catalog_config": "something_new"}
```

### How to use Jinja2 syntax in configuration
From version 0.17.0, `TemplatedConfigLoader` also supports the [Jinja2](https://palletsprojects.com/p/jinja/) template engine alongside the original template syntax. Below is an example of a `catalog.yml` file that uses both features:

```
{% for speed in ['fast', 'slow'] %}
{{ speed }}-trains:
    type: MemoryDataset

{{ speed }}-cars:
    type: pandas.CSVDataset
    filepath: s3://${bucket_name}/{{ speed }}-cars.csv
    save_args:
        index: true

{% endfor %}
```

When parsing this configuration file, `TemplatedConfigLoader` will:

1. Read the `catalog.yml` and compile it using Jinja2
2. Use a YAML parser to parse the compiled config into a Python dictionary
3. Expand `${bucket_name}` in `filepath` using the `globals_pattern` and `globals_dict` arguments for the `TemplatedConfigLoader` instance, as in the previous examples

The output Python dictionary will look as follows:

```python
{
    "fast-trains": {"type": "MemoryDataset"},
    "fast-cars": {
        "type": "pandas.CSVDataset",
        "filepath": "s3://my_s3_bucket/fast-cars.csv",
        "save_args": {"index": True},
    },
    "slow-trains": {"type": "MemoryDataset"},
    "slow-cars": {
        "type": "pandas.CSVDataset",
        "filepath": "s3://my_s3_bucket/slow-cars.csv",
        "save_args": {"index": True},
    },
}
```

```{warning}
Although Jinja2 is a very powerful and extremely flexible template engine, which comes with a wide range of features, we do not recommend using it to template your configuration unless absolutely necessary. The flexibility of dynamic configuration comes at a cost of significantly reduced readability and much higher maintenance overhead. We believe that, for the majority of analytics projects, dynamically compiled configuration does more harm than good.
```


### How to do templating with the `OmegaConfigLoader`
#### Parameters
Templating or [variable interpolation](https://omegaconf.readthedocs.io/en/2.3_branch/usage.html#variable-interpolation), as it's called in `OmegaConf`, for parameters works out of the box if the template values are within the parameter files or the name of the file that contains the template values follows the same config pattern specified for parameters.
By default, the config pattern for parameters is: `["parameters*", "parameters*/**", "**/parameters*"]`.
Suppose you have one parameters file called `parameters.yml` containing parameters with `omegaconf` placeholders like this:

```yaml
model_options:
  test_size: ${data.size}
  random_state: 3
```

and a file containing the template values called `parameters_globals.yml`:
```yaml
data:
  size: 0.2
```

Since both of the file names (`parameters.yml` and `parameters_globals.yml`) match the config pattern for parameters, the `OmegaConfigLoader` will load the files and resolve the placeholders correctly.

#### Catalog
From Kedro `0.18.10` templating also works for catalog files. To enable templating in the catalog you need to ensure that the template values are within the catalog files or the name of the file that contains the template values follows the same config pattern specified for catalogs.
By default, the config pattern for catalogs is: `["catalog*", "catalog*/**", "**/catalog*"]`.

Additionally, any template values in the catalog need to start with an underscore `_`. This is because of how catalog entries are validated. Templated values will neither trigger a key duplication error nor appear in the resulting configuration dictionary.

Suppose you have one catalog file called `catalog.yml` containing entries with `omegaconf` placeholders like this:

```yaml
companies:
  type: ${_pandas.type}
  filepath: data/01_raw/companies.csv
```

and a file containing the template values called `catalog_globals.yml`:
```yaml
_pandas:
  type: pandas.CSVDataset
```

Since both of the file names (`catalog.yml` and `catalog_globals.yml`) match the config pattern for catalogs, the `OmegaConfigLoader` will load the files and resolve the placeholders correctly.

#### Other configuration files
It's also possible to use variable interpolation in configuration files other than parameters and catalog, such as custom spark or mlflow configuration. This works in the same way as variable interpolation in parameter files. You can still use the underscore for the templated values if you want, but it's not mandatory like it is for catalog files.

### How to use global variables with the `OmegaConfigLoader`
From Kedro `0.18.13`, you can use variable interpolation in your configurations using "globals" with `OmegaConfigLoader`.
The benefit of using globals over regular variable interpolation is that the global variables are shared across different configuration types, such as catalog and parameters.
By default, these global variables are assumed to be in files called `globals.yml` in any of your environments. If you want to configure the naming patterns for the files that contain your global variables,
you can do so [by overwriting the `globals` key in `config_patterns`](#how-to-change-which-configuration-files-are-loaded). You can also [bypass the configuration loading](#how-to-bypass-the-configuration-loading-rules)
to directly set the global variables in `OmegaConfigLoader`.

Suppose you have global variables located in the file `conf/base/globals.yml`:
```yaml
my_global_value: 45
dataset_type:
  csv: pandas.CSVDataset
```
You can access these global variables in your catalog or parameters config files with a `globals` resolver like this:
`conf/base/parameters.yml`:
```yaml
my_param : "${globals:my_global_value}"
```
`conf/base/catalog.yml`:
```yaml
companies:
  filepath: data/01_raw/companies.csv
  type: "${globals:dataset_type.csv}"
```
You can also provide a default value to be used in case the global variable does not exist:
```yaml
my_param: "${globals: nonexistent_global, 23}"
```
If there are duplicate keys in the globals files in your base and runtime environments, the values in the runtime environment
overwrite the values in your base environment.

### How to override configuration with runtime parameters with the `OmegaConfigLoader`

Kedro allows you to [specify runtime parameters for the `kedro run` command with the `--params` CLI option](parameters.md#how-to-specify-parameters-at-runtime). These runtime parameters
are added to the `KedroContext` and merged with parameters from the configuration files to be used in your project's pipelines and nodes. From Kedro `0.18.14`, you can use the
`runtime_params` resolver to indicate that you want to override values of certain keys in your configuration with runtime parameters provided through the CLI option.
This resolver can be used across different configuration types, such as parameters, catalog, and more, except for "globals".

Consider this `parameters.yml` file:
```yaml
model_options:
  random_state: "${runtime_params:random}"
```
This will allow you to pass a runtime parameter named `random` through the CLI to specify the value of `model_options.random_state` in your project's parameters:
```bash
kedro run --params random=3
```
You can also specify a default value to be used in case the runtime parameter is not specified with the `kedro run` command. Consider this catalog entry:
```yaml
companies:
  type: pandas.CSVDataset
  filepath: "${runtime_params:folder, 'data/01_raw'}/companies.csv"
```
If the `folder` parameter is not passed through the CLI `--params` option with `kedro run`, the default value `'data/01_raw/'` is used for the `filepath`.

### How to use resolvers in the `OmegaConfigLoader`
Instead of hard-coding values in your configuration files, you can also dynamically compute them using [`OmegaConf`'s
resolvers functionality](https://omegaconf.readthedocs.io/en/2.3_branch/custom_resolvers.html#resolvers). You use resolvers to define custom
logic to calculate values of parameters or catalog entries, or inject these values from elsewhere. To use this feature with Kedro, pass a
`dict` of custom resolvers to `OmegaConfigLoader` through `CONFIG_LOADER_ARGS` in your project's `src/<package_name>/settings.py`.
The example below illustrates this:

```python
import polars as pl
from datetime import date

from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader


def date_today():
    return date.today()


CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "add": lambda *my_list: sum(my_list),
        "polars": lambda x: getattr(pl, x),
        "today": lambda: date_today(),
    }
}
```
These custom resolvers are then registered using `OmegaConf.register_new_resolver()` under the hood and can be used in any of the
configuration files in your project. For example, you can use the `add` or the `today` resolver defined above in your `parameters.yml` like this:
```yaml
model_options:
  test_size: "${add:1,2,3}"
  random_state: 3

date: "${today:}"
```
The values of these parameters will be computed at access time and will be passed on to your nodes.
Resolvers can also be used in your `catalog.yml`. In the example below, we use the `polars` resolver defined above to pass non-primitive
types to the catalog entry.

```yaml
my_polars_dataset:
  type: polars.CSVDataset
  filepath: data/01_raw/my_dataset.csv
  load_args:
    dtypes:
      product_age: "${polars:Float64}"
      group_identifier: "${polars:Utf8}"
    try_parse_dates: true
```
`OmegaConf` also comes with some [built-in resolvers](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#built-in-resolvers)
that you can use with the `OmegaConfigLoader` in Kedro. All built-in resolvers except for [`oc.env`](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#oc-env)
are enabled by default. `oc.env` is only turned on for loading credentials. You can, however, turn this on for all configurations through your project's `src/<package_name>/settings.py` in a similar way:
```{note}
This is an advanced feature and should be used with caution. We do not recommend using environment variables for configurations other than credentials.
```
```python
from omegaconf.resolvers import oc
from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader

CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "oc.env": oc.env,
    }
}
```
### How to load credentials through environment variables
The [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) enables you to load credentials from environment variables. To achieve this you have to use the `OmegaConfigLoader` and the `omegaconf` [`oc.env` resolver](https://omegaconf.readthedocs.io/en/2.3_branch/custom_resolvers.html#oc-env).
To use the `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```python
from kedro.config import OmegaConfigLoader  # new import

CONFIG_LOADER_CLASS = OmegaConfigLoader
```

Now you can use the `oc.env` resolver to access credentials from environment variables in your `credentials.yml`, as demonstrated in the following example:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: ${oc.env:AWS_ACCESS_KEY_ID}
    aws_secret_access_key: ${oc.env:AWS_SECRET_ACCESS_KEY}
```

```{note}
Note that you can only use the resolver in `credentials.yml` and not in catalog or parameter files. This is because we do not encourage the usage of environment variables for anything other than credentials.
```
