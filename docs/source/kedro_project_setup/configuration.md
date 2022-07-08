# Configuration

This section contains detailed information about configuration, for which the relevant API documentation can be found in [kedro.config.ConfigLoader](/kedro.config.ConfigLoader).

## Configuration root

We recommend that you keep all configuration files in the `conf` directory of a Kedro project. However, if you prefer, point Kedro to any other directory and change the configuration paths by setting the `CONF_SOURCE` variable in [`src/<python_package>/settings.py`](settings.md) as follows:
```python
CONF_SOURCE = "new_conf"
```

## Local and base configuration environments

Kedro-specific configuration (e.g., `DataCatalog` configuration for IO) is loaded using the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")
conf_catalog = conf_loader.get("catalog*", "catalog*/**")
```

This recursively scans for configuration files firstly in the `conf/base/` (`base` being the default environment) and then in the `conf/local/` (`local` being the designated overriding environment) directory according to the following rules:

* *Either* of the following is true:
  * filename starts with `catalog`
  * file is located in a sub-directory whose name is prefixed with `catalog`
* *And* file extension is one of the following: `yaml`, `yml`, `json`, `ini`, `pickle`, `xml` or `properties`

Configuration information from files stored in `base` or `local` that match these rules is merged at runtime and returned as a config dictionary:

* If any two configuration files located inside the same environment path (`conf/base/` or `conf/local/` in this example) contain the same top-level key, `load_config` will raise a `ValueError` indicating that the duplicates are not allowed.

* If two configuration files have duplicate top-level keys but are in different environment paths (one in `conf/base/`, another in `conf/local/`, for example) then the last loaded path (`conf/local/` in this case) takes precedence and overrides that key value. `ConfigLoader.get` will not raise any errors - however, a `DEBUG` level log message will be emitted with information on the overridden keys.

Any top-level keys that start with `_` are considered hidden (or reserved) and are ignored after the config is loaded. Those keys will neither trigger a key duplication error nor appear in the resulting configuration dictionary. However, you can still use such keys, for example, as [YAML anchors and aliases](https://support.atlassian.com/bitbucket-cloud/docs/yaml-anchors/).

## Additional configuration environments

In addition to the two built-in local and base configuration environments, you can create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create, such as `conf/server/` or `conf/test/`. To use additional configuration environments, run the following command:

```bash
kedro run --env=test
```

If no `env` option is specified, this will default to using the `local` environment to overwrite `conf/base`.

If, for some reason, your project does not have any other environments apart from `base`, i.e. no `local` environment to default to, you must customise `KedroContext` to take `env="base"` in the constructor and then specify your custom `KedroContext` subclass in `src/<python_package>/settings.py` under the `CONTEXT_CLASS` key.

If you set the `KEDRO_ENV` environment variable to the name of your environment, Kedro will load that environment for your `kedro run`, `kedro ipython`, `kedro jupyter notebook` and `kedro jupyter lab` sessions:

```bash
export KEDRO_ENV=test
```

```{note}
If you both specify the `KEDRO_ENV` environment variable and provide the `--env` argument to a CLI command, the CLI argument takes precedence.
```

## Template configuration

Kedro also provides an extension [TemplatedConfigLoader](/kedro.config.TemplatedConfigLoader) class that allows you to template values in configuration files. To apply templating in your project, set the `CONFIG_LOADER_CLASS` constant in your `src/<python_package>/settings.py`:

```python
from kedro.config import TemplatedConfigLoader  # new import

...
CONFIG_LOADER_CLASS = TemplatedConfigLoader
...
```

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

The contents of the dictionary resulting from `globals_pattern` are merged with the `globals_dict` dictionary. In case of conflicts, the keys from the `globals_dict` dictionary take precedence. The resulting global dictionary prepared by `TemplatedConfigLoader` will look like this:

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

### Jinja2 support

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


## Parameters

### Load parameters

Parameters project configuration can be loaded with the help of the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")
parameters = conf_loader.get("parameters*", "parameters*/**")
```

This will load configuration files from any subdirectories in `conf` that have a filename starting with `parameters`, or are located inside a folder with name starting with `parameters`.

```{note}
Since `local` is set as the environment, the configuration path `conf/local` takes precedence in the example above. Hence any overlapping top-level keys from `conf/base` will be overwritten by the ones from `conf/local`.
```

Calling `conf_loader.get()` in the example above will throw a `MissingConfigException` error if no configuration files match the given patterns in any of the specified paths. If this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import ConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")

try:
    parameters = conf_loader.get("parameters*", "parameters*/**", "**/parameters*")
except MissingConfigException:
    parameters = {}
```

```{note}
The `kedro.framework.context.KedroContext` class uses the approach above to load project parameters.
```

[Parameters can then be used on their own or fed in as function inputs.](#use-parameters)

### Specify parameters at runtime

Kedro also allows you to specify runtime parameters for the `kedro run` CLI command. To do so, use the `--params` command line option and specify a comma-separated list of key-value pairs that will be added to [KedroContext](/kedro.framework.context.KedroContext) parameters and made available to pipeline nodes. Each key-value pair is split on the first colon. For example:

```bash
kedro run --params param_key1:value1,param_key2:2.0  # this will add {"param_key1": "value1", "param_key2": 2} to parameters dictionary
```

Values provided in the CLI take precedence and overwrite parameters specified in configuration files. Parameter keys are _always_ treated as strings. Parameter values are converted to a float or an integer number if the corresponding conversion succeeds; otherwise, they are also treated as string.

If any extra parameter key and/or value contains spaces, wrap the whole option contents in quotes:

```bash
kedro run --params "key1:value with spaces,key2:value"
```

Since key-value pairs are split on the first colon, values can contain colons, but keys cannot. This is a valid CLI command:

```bash
kedro run --params endpoint_url:https://endpoint.example.com
```

### Use parameters

Say you have a set of parameters you're playing around with that specify modelling hyperparameters. You can declare these in one place, for instance `conf/base/parameters.yml`, so that you isolate your changes in one central location.

```yaml
step_size: 1
learning_rate: 0.01
```

 You can now use the `params:` prefix to reference these parameters in the `node` definition:

```python
def increase_volume(volume, step):
    return volume + step


# in pipeline definition
node(
    func=increase_volume,
    inputs=["input_volume", "params:step_size"],
    outputs="output_volume",
)
```

You can also group your parameters into nested structures and, using the same method above, load them by top-level key:

```yaml
step_size: 1
model_params:
    learning_rate: 0.01
    test_data_ratio: 0.2
    number_of_train_iterations: 10000
```


```python
def train_model(data, model):
    lr = model["learning_rate"]
    test_data_ratio = model["test_data_ratio"]
    iterations = model["number_of_train_iterations"]
    ...


# in pipeline definition
node(
    func=train_model,
    inputs=["input_data", "params:model_params"],
    outputs="output_data",
)
```

Alternatively, you can also pass `parameters` to the node inputs and get access to the entire collection of values inside the node function.

```python
def increase_volume(volume, params):
    step = params["step_size"]
    return volume + step


# in pipeline definition
node(
    func=increase_volume, inputs=["input_volume", "parameters"], outputs="output_volume"
)
```

In both cases, under the hood parameters are added to the Data Catalog through the method `add_feed_dict()` in [`DataCatalog`](/kedro.io.DataCatalog), where they live as `MemoryDataSet`s. This method is also what the `KedroContext` class uses when instantiating the catalog.

```{note}
You can use `add_feed_dict()` to inject any other entries into your `DataCatalog` as per your use case.
```

## Credentials

For security reasons, we strongly recommend you to *not* commit any credentials or other secrets to the Version Control System. Hence, by default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not committed to your git repository.

Credentials configuration can be loaded the same way as any other project configuration using the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")
credentials = conf_loader.get("credentials*", "credentials*/**")
```

This will load configuration files from `conf/base` and `conf/local` whose filenames start with `credentials`, or that are located inside a folder with a name that starts with `credentials`.

```{note}
Since `local` is set as the environment, the configuration path `conf/local` takes precedence in the example above. Hence, any overlapping top-level keys from `conf/base` will be overwritten by the ones from `conf/local`.
```

Calling `conf_loader.get()` in the example above throws a `MissingConfigException` error if no configuration files match the given patterns in any of the specified paths. If this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import ConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")

try:
    credentials = conf_loader.get("credentials*", "credentials*/**")
except MissingConfigException:
    credentials = {}
```

```{note}
The `kedro.framework.context.KedroContext` class uses the approach above to load project credentials.
```

Credentials configuration can then be used on its own or [fed into the `DataCatalog`](../data/data_catalog.md#feeding-in-credentials).

### AWS credentials

When you work with AWS credentials on datasets, you are not required to store AWS credentials in the project configuration files. Instead, you can specify them using environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, optionally, `AWS_SESSION_TOKEN`. Please refer to the [official documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.

## Configure `kedro run` arguments

An extensive list of CLI options for a `kedro run` is available in the [Kedro CLI documentation](../development/commands_reference.md#run-the-project). However, instead of specifying all the command line options in a `kedro run` via the CLI, you can specify a config file that contains the arguments, say `config.yml` and run:

```console
$ kedro run --config config.yml
```

where `config.yml` is formatted as below (for example):

```yaml
run:
  tag:
    - tag1
    - tag2
    - tag3
  pipeline: pipeline1
  parallel: true
  node_names:
    - node1
    - node2
  env: env1
```

```{note}
If you provide both a configuration file and a CLI option that clashes with the configuration file, the CLI option will take precedence.
```
