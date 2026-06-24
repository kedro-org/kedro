# How to work with templating

This guide shows you how to work with templating in your Kedro project.

## On this page

- [How to template parameters](#how-to-template-parameters)
- [How to template catalog files](#how-to-template-catalog-files)
- [How to template other configuration files](#how-to-template-other-configuration-files)
- [How to load a data catalog with templating in code](#how-to-load-a-data-catalog-with-templating-in-code)
- [How to use global variables with the `OmegaConfigLoader`](#how-to-use-global-variables-with-the-omegaconfigloader)
- [How to override configuration with runtime parameters with the `OmegaConfigLoader`](#how-to-override-configuration-with-runtime-parameters-with-the-omegaconfigloader)
- [How to use resolvers in the `OmegaConfigLoader`](#how-to-use-resolvers-in-the-omegaconfigloader)

## How to template parameters

Templating, or [variable interpolation](https://omegaconf.readthedocs.io/en/2.3_branch/usage.html#variable-interpolation) as `OmegaConf` calls it, works out of the box for parameters. The template values must be within the parameter files, or the name of the file that contains them must follow the same config pattern specified for parameters.
By default, the config pattern for parameters is: `["parameters*", "parameters*/**", "**/parameters*"]`.
Suppose you have one parameters file called `parameters.yml` containing parameters with `omegaconf` placeholders like this:

```yaml
model_options:
  test_size: ${data.size}
  random_state: 3
```

and a file containing the template values called `parameters_variables.yml`. The file name can be anything as long as it matches the config pattern for parameters:
```yaml
data:
  size: 0.2
```

Since both of the file names (`parameters.yml` and `parameters_variables.yml`) match the config pattern for parameters, the `OmegaConfigLoader` will load the files and resolve the placeholders as expected.

## How to template catalog files

From Kedro `0.18.10` templating also works for catalog files. To enable it, ensure that the template values are within the catalog files. Or, the name of the file that contains them must follow the same config pattern specified for catalogs.
By default, the config pattern for catalogs is: `["catalog*", "catalog*/**", "**/catalog*"]`.

Any template values in the catalog need to start with an underscore `_`. This is because of how catalog entries are validated. Templated values will neither trigger a key duplication error nor appear in the resulting configuration dictionary.

Suppose you have one catalog file called `catalog.yml` containing entries with `omegaconf` placeholders like this:

```yaml
companies:
  type: ${_pandas.type}
  filepath: data/01_raw/companies.csv
```

and a file containing the template values called `catalog_variables.yml`:
```yaml
_pandas:
  type: pandas.CSVDataset
```

Since both of the file names (`catalog.yml` and `catalog_variables.yml`) match the config pattern for catalogs, the `OmegaConfigLoader` will load the files and resolve the placeholders as expected.

## How to template other configuration files

It's also possible to use variable interpolation in configuration files other than parameters and catalog, such as custom Spark or MLflow configuration. This works in the same way as variable interpolation in parameter files. You can still use the underscore for the templated values if you want, but it's not mandatory like it is for catalog files.

## How to load a data catalog with templating in code

You can use the `OmegaConfigLoader` to directly load a data catalog that contains templating in code. Internally the `OmegaConfigLoader` resolves any templates, so no further steps are required to load catalog entries properly.
```yaml
# Example catalog with templating
companies:
  type: ${_dataset_type}
  filepath: data/01_raw/companies.csv

_dataset_type: pandas.CSVDataset
```

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

# Instantiate an `OmegaConfigLoader` instance with the location of your project configuration.
conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

conf_catalog = conf_loader["catalog"]
# conf_catalog["companies"]
# Will result in: {'type': 'pandas.CSVDataset', 'filepath': 'data/01_raw/companies.csv'}
```

## How to use global variables with the `OmegaConfigLoader`

From Kedro `0.18.13`, you can use variable interpolation in your configurations using "globals" with `OmegaConfigLoader`.
The benefit of using globals over regular variable interpolation is that the global variables are shared across different configuration types, such as catalog and parameters.
By default, these global variables are assumed to be in files called `globals.yml` in any of your environments. If you want to configure the naming patterns for the files that contain your global variables,
you can do so [by overwriting the `globals` key in `config_patterns`](how_to_configure_project.md#how-to-change-which-configuration-files-are-loaded). You can also [bypass the configuration loading](how_to_configure_project.md#how-to-bypass-the-configuration-loading-rules)
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

## How to override configuration with runtime parameters with the `OmegaConfigLoader`

Kedro allows you to [specify runtime parameters for the `kedro run` command with the `--params` CLI option](how_to_use_parameters_and_credentials.md#how-to-specify-parameters-at-runtime). These runtime parameters
are added to the `KedroContext` and merged with parameters from the configuration files to be used in your project's pipelines and nodes. From Kedro `0.18.14`, you can use the
`runtime_params` resolver to show that you want to override values of certain keys in your configuration with runtime parameters provided through the CLI option.
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

!!! note
    When manually instantiating `OmegaConfigLoader` in code, runtime parameters passed through the CLI `--params` option will not be available to the resolver. This occurs because the manually created config loader instance doesn't have access to the runtime parameters provided through the CLI.
    If you need to access runtime parameters in code that manually instantiates `OmegaConfigLoader`, you should instead use the Kedro context to access parameters.

### How to use `globals` and `runtime_params`

As mentioned above, `runtime_params` are not designed to override `globals` configuration. This is done to avoid unexplicit overrides and to simplify parameter resolutions. Thus, `globals` has a single entry point - the `yaml` file.

You can still use `globals` and `runtime_params` by specifying `globals` as a default value to be used in case the runtime parameter is not passed.

Consider this `parameters.yml`:
```yaml
model_options:
  random_state: "${runtime_params:random, ${globals:my_global_value}}"
```

and this `globals.yml` file:

```yaml
my_global_value: 4
```

This will allow you to pass a runtime parameter named `random` through the CLI to specify the value of `model_options.random_state` in your project's parameters:
```bash
kedro run --params random=3
```

If the `random` parameter is not passed through the CLI `--params` option with `kedro run`, then `my_global_value` from `globals.yml` is used for the `model_options.random_state`.

## How to use resolvers in the `OmegaConfigLoader`

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
        "today": date_today,
    }
}
```
These custom resolvers are then registered using `OmegaConf.register_new_resolver()` internally and can be used in any of the
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
are enabled by default. `oc.env` is enabled solely for loading credentials. You can also turn this on for all configurations through your project's `src/<package_name>/settings.py` in a similar way:

!!! note
    This is an advanced feature and should be used with caution. We do not recommend using environment variables for configurations other than credentials.

```python
from omegaconf.resolvers import oc

CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "oc.env": oc.env,
    }
}
```

### How to use custom resolvers with `OmegaConfigLoader`

You can register custom resolvers to use non-primitive types for parameters.

Consider the following `parameters.yml` file an example of Python script for registering a custom resolver:

```yaml
polars_float64: "${polars: Float64}"
today: "${today:}"
```

```python
import polars as pl
from datetime import date

from kedro.config import OmegaConfigLoader

custom_resolvers = {"polars": lambda x: getattr(pl, x),
                    "today": lambda: date.today()}

# Register custom resolvers
config_loader = OmegaConfigLoader(conf_source=".", custom_resolvers=custom_resolvers)

print(config_loader["parameters"])
```

If you run it from the same directory where `parameters.yml` placed it gives the following output:

```console
{'polars_float64': Float64, 'today': datetime.date(2023, 11, 23)}
```
