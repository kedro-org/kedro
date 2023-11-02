# Advanced configuration
The documentation on [configuration](./configuration_basics.md) describes how to satisfy most common requirements of standard Kedro project configuration:

By default, Kedro is set up to use the [OmegaConfigLoader](/kedro.config.OmegaConfigLoader) class.

This page also contains a set of guidance for advanced configuration requirements of standard Kedro projects:

* [How to use a custom config loader](#how-to-use-a-custom-configuration-loader)
* [How to change which configuration files are loaded](#how-to-change-which-configuration-files-are-loaded)
* [How to ensure non default configuration files get loaded](#how-to-ensure-non-default-configuration-files-get-loaded)
* [How to bypass the configuration loading rules](#how-to-bypass-the-configuration-loading-rules)
* [How to do templating with the `OmegaConfigLoader`](#how-to-do-templating-with-the-omegaconfigloader)
* [How to use global variables with the `OmegaConfigLoader`](#how-to-use-global-variables-with-the-omegaconfigloader)
* [How to override configuration with runtime parameters with the `OmegaConfigLoader`](#how-to-override-configuration-with-runtime-parameters-with-the-omegaconfigloader)
* [How to use resolvers in the `OmegaConfigLoader`](#how-to-use-resolvers-in-the-omegaconfigloader)
* [How to load credentials through environment variables with `OmegaConfigLoader`](#how-to-load-credentials-through-environment-variables)


## How to use a custom configuration loader
You can implement a custom configuration loader by extending the [`AbstractConfigLoader`](/kedro.config.AbstractConfigLoader) class:

```python
from kedro.config import AbstractConfigLoader


class CustomConfigLoader(AbstractConfigLoader):
    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
    ):
        super().__init__(
            conf_source=conf_source, env=env, runtime_params=runtime_params
        )

        # Custom implementation
```
To use this custom configuration loader, set it as the project configuration loader in `src/<package_name>/settings.py` as follows:
```python
from package_name.custom_configloader import CustomConfigLoader

CONFIG_LOADER_CLASS = CustomConfigLoader
```


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

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

# Bypass configuration patterns by setting the key and values directly on the config loader instance.
conf_loader["catalog"] = {"catalog_config": "something_new"}
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

CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "oc.env": oc.env,
    }
}
```
### How to load credentials through environment variables
The [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) enables you to load credentials from environment variables. To achieve this you have to use the `OmegaConfigLoader` and the `omegaconf` [`oc.env` resolver](https://omegaconf.readthedocs.io/en/2.3_branch/custom_resolvers.html#oc-env).
You can use the `oc.env` resolver to access credentials from environment variables in your `credentials.yml`:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: ${oc.env:AWS_ACCESS_KEY_ID}
    aws_secret_access_key: ${oc.env:AWS_SECRET_ACCESS_KEY}
```

```{note}
Note that you can only use the resolver in `credentials.yml` and not in catalog or parameter files. This is because we do not encourage the usage of environment variables for anything other than credentials.
```
