### Configuration patterns

This logic is specified by `config_patterns` in the configuration loader classes. By default those patterns are set as follows for the configuration of catalog, parameters, logging and credentials:

```python
config_patterns = {
    "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
    "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
    "logging": ["logging*", "logging*/**", "**/logging*"],
}
```

The configuration patterns can be changed by setting the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](settings.md). You can change the default patterns as well as add additional ones, for example, for Spark configuration files.
This example shows how to load `parameters` if your files are using a `params` naming convention instead of `parameters` and how to add patterns to load Spark configuration:

```python
CONFIG_LOADER_ARGS = {
    "config_patterns": {
        "spark": ["spark*/"],
        "parameters": ["params*", "params*/**", "**/params*"],
    }
}
```

You can also bypass the configuration patterns and set configuration directly on the instance of a config loader class. You can bypass the default configuration (catalog, parameters, credentials, and logging) as well as additional configuration.

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path)

# Bypass configuration patterns by setting the key and values directly on the config loader instance.
conf_loader["catalog"] = {"catalog_config": "something_new"}
```

Configuration information from files stored in `base` or `local` that match these rules is merged at runtime and returned as a config dictionary:

* If any two configuration files located inside the same environment path (`conf/base/` or `conf/local/` in this example) contain the same top-level key, `load_config` will raise a `ValueError` indicating that duplicates are not allowed.

* If two configuration files have duplicate top-level keys but are in different environment paths (one in `conf/base/`, another in `conf/local/`, for example) then the last loaded path (`conf/local/` in this case) takes precedence and overrides that key value. `ConfigLoader.get` will not raise any errors - however, a `DEBUG` level log message will be emitted with information on the overridden keys.

When using the default `ConfigLoader` or the `TemplatedConfigLoader`, any top-level keys that start with `_` are considered hidden (or reserved) and are ignored after the config is loaded. Those keys will neither trigger a key duplication error nor appear in the resulting configuration dictionary. However, you can still use such keys, for example, as [YAML anchors and aliases](https://www.educative.io/blog/advanced-yaml-syntax-cheatsheet#anchors).

### Additional configuration environments

In addition to the two built-in local and base configuration environments, you can create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create, such as `conf/server/` or `conf/test/`. To use additional configuration environments, run the following command:

```bash
kedro run --env=<your-environment>
```

If no `env` option is specified, this will default to using the `local` environment to overwrite `conf/base`.

If you set the `KEDRO_ENV` environment variable to the name of your environment, Kedro will load that environment for your `kedro run`, `kedro ipython`, `kedro jupyter notebook` and `kedro jupyter lab` sessions:

```bash
export KEDRO_ENV=<your-environment>
```

```{note}
If you both specify the `KEDRO_ENV` environment variable and provide the `--env` argument to a CLI command, the CLI argument takes precedence.
```


#### Using only one configuration environment

If, for some reason, your project does not have any other environments apart from `base`, i.e. no `local` environment to default to, you must customise the configuration loader you're using to take `env="base"` in the constructor and then specify your custom config loader subclass in `src/<package_name>/settings.py` under the `CONFIG_LOADER_CLASS` key.
Below is an example of such a custom class. If you're using the `TemplatedConfigLoader` or the `OmegaConfigLoader` you need to use either of those as the class you are subclassing.

```python
# src/<package_name>/custom_config.py

from kedro.config import ConfigLoader
from typing import Any, Dict


class CustomConfigLoader(ConfigLoader):
    def __init__(
            self,
            conf_source: str,
            env: str = None,
            runtime_params: Dict[str, Any] = None,
    ):
        super().__init__(conf_source=conf_source, env="base", runtime_params=runtime_params)
```

And then you can import your `CustomConfigLoader` from `settings.py`:

```python
# settings.py
from package_name.custom_configloader import CustomConfigLoader

CONFIG_LOADER_CLASS = CustomConfigLoader
```


## Specify the configuration loader class

By default, Kedro is set up to use the [ConfigLoader](/kedro.config.ConfigLoader) class. Kedro also provides two additional configuration loaders with more advanced functionality: the [TemplatedConfigLoader](/kedro.config.TemplatedConfigLoader) and the [OmegaConfigLoader](/kedro.config.OmegaConfigLoader).
Each of these classes are alternatives for the default `ConfigLoader` and have different features. The following sections will describe each of these classes and their specific functionality in more detail.

### TemplatedConfigLoader

Kedro provides an extension [TemplatedConfigLoader](/kedro.config.TemplatedConfigLoader) class that allows you to template values in configuration files. To apply templating in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](settings.md):

```python
from kedro.config import TemplatedConfigLoader  # new import

CONFIG_LOADER_CLASS = TemplatedConfigLoader
```

#### Provide template values through globals
When using the `TemplatedConfigLoader` you can provide values in the configuration template through a `globals` file or dictionary.

Let's assume the project contains a `conf/base/globals.yml` file with the following contents:

```yaml
bucket_name: "my_s3_bucket"
key_prefix: "my/key/prefix/"

datasets:
    csv: "pandas.CSVDataSet"
    spark: "spark.SparkDataSet"

folders:
    raw: "01_raw"
    int: "02_intermediate"
    pri: "03_primary"
    fea: "04_feature"
```

To point your `TemplatedConfigLoader` to the globals file, add it to the the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](settings.md):

```python
CONFIG_LOADER_ARGS = {"globals_pattern": "*globals.yml"}
```

Alternatively, you can declare which values to fill in the template through a dictionary. This dictionary could look like the below:

```python
{
    "bucket_name": "another_bucket_name",
    "non_string_key": 10,
    "key_prefix": "my/key/prefix",
    "datasets": {"csv": "pandas.CSVDataSet", "spark": "spark.SparkDataSet"},
    "folders": {
        "raw": "01_raw",
        "int": "02_intermediate",
        "pri": "03_primary",
        "fea": "04_feature",
    },
}
```

To point your `TemplatedConfigLoader` to the globals dictionary, add it to the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](settings.md):

```python
CONFIG_LOADER_ARGS = {
    "globals_dict": {
        "bucket_name": "another_bucket_name",
        "non_string_key": 10,
        "key_prefix": "my/key/prefix",
        "datasets": {"csv": "pandas.CSVDataSet", "spark": "spark.SparkDataSet"},
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

#### Use Jinja2 syntax in configuration

From version 0.17.0, `TemplateConfigLoader` also supports the [Jinja2](https://palletsprojects.com/p/jinja/) template engine alongside the original template syntax. Below is an example of a `catalog.yml` file that uses both features:

```
{% for speed in ['fast', 'slow'] %}
{{ speed }}-trains:
    type: MemoryDataSet

{{ speed }}-cars:
    type: pandas.CSVDataSet
    filepath: s3://${bucket_name}/{{ speed }}-cars.csv
    save_args:
        index: true

{% endfor %}
```

When parsing this configuration file, `TemplateConfigLoader` will:

1. Read the `catalog.yml` and compile it using Jinja2
2. Use a YAML parser to parse the compiled config into a Python dictionary
3. Expand `${bucket_name}` in `filepath` using the `globals_pattern` and `globals_dict` arguments for the `TemplateConfigLoader` instance, as in the previous examples

The output Python dictionary will look as follows:

```python
{
    "fast-trains": {"type": "MemoryDataSet"},
    "fast-cars": {
        "type": "pandas.CSVDataSet",
        "filepath": "s3://my_s3_bucket/fast-cars.csv",
        "save_args": {"index": True},
    },
    "slow-trains": {"type": "MemoryDataSet"},
    "slow-cars": {
        "type": "pandas.CSVDataSet",
        "filepath": "s3://my_s3_bucket/slow-cars.csv",
        "save_args": {"index": True},
    },
}
```

```{warning}
Although Jinja2 is a very powerful and extremely flexible template engine, which comes with a wide range of features, we do not recommend using it to template your configuration unless absolutely necessary. The flexibility of dynamic configuration comes at a cost of significantly reduced readability and much higher maintenance overhead. We believe that, for the majority of analytics projects, dynamically compiled configuration does more harm than good.
```

### OmegaConfigLoader

[OmegaConf](https://omegaconf.readthedocs.io/) is a Python library for configuration. It is a YAML-based hierarchical configuration system with support for merging configurations from multiple sources.
From Kedro 0.18.5 you can use the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) which uses `OmegaConf` under the hood to load data.

```{note}
`OmegaConfigLoader` is under active development and will be available from Kedro 0.18.5. New features will be added in future releases. Let us know if you have any feedback about the `OmegaConfigLoader` or ideas for new features.
```

The `OmegaConfigLoader` can load `YAML` and `JSON` files. Acceptable file extensions are `.yml`, `.yaml`, and `.json`. By default, any configuration files used by the config loaders in Kedro are `.yml` files.

To use the `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](settings.md):

```python
from kedro.config import OmegaConfigLoader  # new import

CONFIG_LOADER_CLASS = OmegaConfigLoader
```

#### Templating for parameters
Templating or [variable interpolation](https://omegaconf.readthedocs.io/en/2.3_branch/usage.html#variable-interpolation), as it's called in `OmegaConf`, for parameters works out of the box if one condition is met: the name of the file that contains the template values must follow the same config pattern specified for parameters.
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

#### Custom template resolvers
`Omegaconf` provides functionality to [register custom resolvers](https://omegaconf.readthedocs.io/en/2.3_branch/usage.html#resolvers) for templated values. You can use these custom resolves within Kedro by extending the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) class.
The example below illustrates this:

```python
from kedro.config import OmegaConfigLoader
from omegaconf import OmegaConf
from typing import Any, Dict


class CustomOmegaConfigLoader(OmegaConfigLoader):
    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
    ):
        super().__init__(
            conf_source=conf_source, env=env, runtime_params=runtime_params
        )

        # Register a customer resolver that adds up numbers.
        self.register_custom_resolver("add", lambda *numbers: sum(numbers))

    @staticmethod
    def register_custom_resolver(name, function):
        """
        Helper method that checks if the resolver has already been registered and registers the
        resolver if it's new. The check is needed, because omegaconf will throw an error
        if a resolver with the same name is registered twice.
        Alternatively, you can call `register_new_resolver()` with  `replace=True`.
        """
        if not OmegaConf.has_resolver(name):
            OmegaConf.register_new_resolver(name, function)
```

In order to use this custom configuration loader, you will need to set it as the project configuration loader in `src/<package_name>/settings.py`:

```python
from package_name.custom_configloader import CustomOmegaConfigLoader

CONFIG_LOADER_CLASS = CustomOmegaConfigLoader
```

You can then use the custom "add" resolver in your `parameters.yml` as follows:

```yaml
model_options:
  test_size: ${add:1,2,3}
  random_state: 3
```

#### Environment variables for credentials
The [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) enables you to load credentials from environment variables. To achieve this you have to use the `omegaconf` [`oc.env` resolver](https://omegaconf.readthedocs.io/en/2.3_branch/custom_resolvers.html#oc-env).
This is an example of how you can access credentials from environment variables in `credentials.yml`:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: ${oc.env:AWS_ACCESS_KEY_ID}
    aws_secret_access_key: ${oc.env:AWS_SECRET_ACCESS_KEY}
```

```{note}
Note that you can only use the resolver in `credentials.yml` and not in catalog or parameter files. This is because we do not encourage the usage of environment variables for anything other than credentials.
```
