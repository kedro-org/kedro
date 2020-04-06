# Configuration

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.
>
> This section contains detailed information about configuration.

Relevant API documentation: [ConfigLoader](/kedro.config.ConfigLoader)

## Local and base configuration

We recommend that you keep all configuration files in the `conf` directory of a Kedro project. However, if you prefer, you may point Kedro to any other directory and change the configuration paths by overriding `CONF_ROOT` variable from the derived `ProjectContext` class in `src/<project-package>/run.py` as follows:
```python
class ProjectContext(KedroContext):
    CONF_ROOT = "new_conf"
    # ...
```

## Loading

Kedro-specific configuration (e.g., `DataCatalog` configuration for IO) is loaded using the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)
conf_catalog = conf_loader.get("catalog*", "catalog*/**")
```

This will recursively scan for configuration files firstly in `conf/base/` and then in `conf/local/` directory according to the following rules:

* ANY of the following is true:
  * filename starts with `catalog` OR
  * file is located in a sub-directory whose name is prefixed with `catalog`
* AND file extension is one of the following: `yaml`, `yml`, `json`, `ini`, `pickle`, `xml` or `properties`

Configuration information from files stored in `base` or `local` that match these rules is merged at runtime and returned in the form of a config dictionary:

* If any 2 configuration files located inside the same environment path (`conf/base/` or `conf/local/` in this example) contain the same top-level key, `load_config` will raise a `ValueError` indicating that the duplicates are not allowed.

> *Note:* Any top-level keys that start with `_` character are considered hidden (or reserved) and therefore are ignored right after the config load. Those keys will neither trigger a key duplication error mentioned above, nor will they appear in the resulting configuration dictionary. However, you may still use such keys for various purposes. For example, as [YAML anchors and aliases](https://confluence.atlassian.com/bitbucket/yaml-anchors-960154027.html).

* If 2 configuration files have duplicate top-level keys, but are placed into different environment paths (one in `conf/base/`, another in `conf/local/`, for example) then the last loaded path (`conf/local/` in this case) takes precedence and overrides that key value. `ConfigLoader.get(<pattern>, ...)` will not raise any errors, however a `DEBUG` level log message will be emitted with the information on the over-ridden keys.
* If the same environment path is passed multiple times, a `UserWarning` will be emitted to draw attention to the duplicate loading attempt, and any subsequent loading after the first one will be skipped.


## Additional configuration environments

In addition to the 2 built-in configuration environments, it is possible to create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create. You are be able to create environments like `conf/server/`, `conf/test/`, etc. Any additional configuration environments can be created inside `conf` folder and loaded by running the following command:

```bash
kedro run --env=test
```

If no `env` option is specified, this will default to using `local` environment to overwrite `conf/base`.

You can alternatively pass a different environment value in the constructor of `ProjectContext` in `src/run.py`.

```python
env = "test"
```

> *Note*: If, for some reason, your project does not have any other environments apart from `base`, i.e. no `local` environment to default to, the recommended course of action is to use the approach above, namely customise your `ProjectContext` to take `env="base"` in the constructor.

If you set the `KEDRO_ENV` environment variable to the name of your environment, Kedro will load that environment for your `kedro run`, `kedro ipython`, `kedro jupyter notebook` and `kedro jupyter lab` sessions.

```bash
export KEDRO_ENV=test
```

> *Note*: If you specify both the `KEDRO_ENV` environment variable and provide the `--env` argument to a CLI command, the CLI argument takes precedence.

## Templating configuration

Kedro also provides an extension [TemplatedConfigLoader](/kedro.config.TemplatedConfigLoader) class that allows to template values in your configuration files. `TemplatedConfigLoader` is available in `kedro.config`, to apply templating to your `ProjectContext` in `src/<project-name>/run.py`, you will need to overwrite the `_create_config_loader` method as follows:

```python
from kedro.config import TemplatedConfigLoader  # new import


class ProjectContext(KedroContext):
    def _create_config_loader(self, conf_paths: Iterable[str]) -> TemplatedConfigLoader:
        return TemplatedConfigLoader(
            conf_paths,
            globals_pattern="*globals.yml",  # read the globals dictionary from project config
            globals_dict={  # extra keys to add to the globals dictionary, take precedence over globals_pattern
                "bucket_name": "another_bucket_name",
                "non_string_key": 10,
            },
        )
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
    fea: "04_features"
```

The contents of the dictionary resulting from `globals_pattern` get merged with the `globals_dict` dictionary. In case of conflicts, the keys from the `globals_dict` dictionary take precedence. The resulting global dictionary prepared by `TemplatedConfigLoader` will look like this:

```python
{
    "bucket_name": "another_bucket_name",
    "non_string_key": 10,
    "key_prefix": "my/key/prefix",
    "datasets": {
        "csv": "pandas.CSVDataSet",
        "spark": "spark.SparkDataSet"
    },
    "folders": {
        "raw": "01_raw",
        "int": "02_intermediate",
        "pri": "03_primary",
        "fea": "04_features",
    },
}
```

Now the templating can be applied to the configs. Here is an example of a templated `conf/base/catalog.yml`:

```yaml
raw_boat_data:
    type: "${datasets.spark}"  # nested paths into global dict are allowed
    filepath: "s3a://${bucket_name}/${key_prefix}/${folders.raw}/boats.csv"
    file_format: parquet

raw_car_data:
    type: "${datasets.csv}"
    filepath: "s3://${bucket_name}/data/${key_prefix}/${folders.raw}/${filename|cars.csv}"  # default to 'cars.csv' if the 'filename' key is not found in the global dict
```

> Note: `TemplatedConfigLoader` uses `jmespath` package in the background to extract elements from global dictionary. For more information about JMESPath syntax please see: https://github.com/jmespath/jmespath.py.


## Parameters

### Loading parameters

Parameters project configuration can be loaded with the help of the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)
parameters = conf_loader.get("parameters*", "parameters*/**")
```

The code snippet above will load all configuration files from `conf/base` and `conf/local`, which either have the filename starting with `parameters` or are located inside a folder with name starting with `parameters`.

> *Note:* Configuration path `conf/local` takes precedence in the example above since it's loaded last, therefore any overlapping top-level keys from `conf/base` will be overwritten by the ones from `conf/local`.

Calling `conf_loader.get()` in the example above will throw a `MissingConfigException` error if there are no configuration files matching the given patterns in any of the specified paths. If this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import ConfigLoader, MissingConfigException

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)

try:
    parameters = conf_loader.get("parameters*", "parameters*/**")
except MissingConfigException:
    parameters = {}
```

> *Note:* `kedro.context.KedroContext` class uses the approach above to load project parameters.

Parameters can then be used on their own or fed in as function inputs, as described in [this section](#using-parameters) below.

### Specifying parameters at runtime

Kedro also allows you to specify runtime parameters for `kedro run` CLI command. To do that, you need to add the `--params` command line option and specify a comma-separated list of key-value pairs that will be added to [KedroContext](/kedro.context.KedroContext) parameters and made available to pipeline nodes. Each key-value pair is split on the first colon. Here is an example of triggering Kedro run with extra parameters specified:

```bash
kedro run --params param_key1:value1,param_key2:2.0  # this will add {"param_key1": "value1", "param_key2": 2} to parameters dictionary
```

> Note: Parameter keys are _always_ treated as strings. Parameter values are converted to a float or an integer number if the corresponding conversion succeeds, otherwise they are also treated as string.

> Note: If, for example, `param_key1` parameter has already been defined in the project configuration, the value provided in the CLI option will take precedence and will overwrite the one from the configuration.

> Tip: Since key-value pairs are split on the first colon, values can contain colons, but the keys cannot. This is a valid CLI command:
>
> `kedro run --params endpoint_url:https://endpoint.example.com`

> Tip: If any extra parameter key and/or value contains spaces, wrap the whole option contents into quotes:
>
> `kedro run --params "key1:value with spaces,key2:value"`

### Using parameters

Say you have a set of parameters you're playing around with for your model. You can declare these in one place, for instance `conf/base/parameters.yml`, so that you isolate your changes to one central location.

```yaml
step_size: 1
learning_rate: 0.01
```

 You may now reference these parameters in the `node` definition, using the `params:` prefix:

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

In both cases, what happened under the hood is that the parameters had been added to the Data Catalog through the method `add_feed_dict()` (Relevant API documentation: [DataCatalog](/kedro.io.DataCatalog)), where they live as `MemoryDataSet`s. This method is also what the `KedroContext` class uses when instantiating the catalog.

> *Note*: You can use `add_feed_dict()` to inject any other entries into your `DataCatalog` as per your use case.



## Credentials

> *Note:* For security reasons, we strongly recommend *not* committing any credentials or other secrets to the Version Control System. Hence, by default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not committed to your git repository.

Credentials configuration can be loaded the same way as any other project configuration using the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)
credentials = conf_loader.get("credentials*", "credentials*/**")
```

This will load all configuration files from `conf/base` and `conf/local`, which either have the filename starting with `credentials` or are located inside a folder with name starting with `credentials`.

> *Note:* Configuration path `conf/local` takes precedence in the example above since it's loaded last, therefore any overlapping top-level keys from `conf/base` will be overwritten by the ones from `conf/local`.

Calling `conf_loader.get()` in the example above will throw a `MissingConfigException` error if there are no configuration files matching the given patterns in any of the specified paths. If this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import ConfigLoader, MissingConfigException

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)

try:
    credentials = conf_loader.get("credentials*", "credentials*/**")
except MissingConfigException:
    credentials = {}
```

> *Note:* `kedro.context.KedroContext` class uses the approach above to load project credentials.

Credentials configuration can then be used on its own or fed into the `DataCatalog` as described in [this section](./04_data_catalog.md#feeding-in-credentials).

### AWS credentials

When working with AWS credentials on datasets, you are not required to store AWS credentials in the project configuration files. Instead, you can specify them using environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, optionally, `AWS_SESSION_TOKEN`. Please refer to the [official documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.

## Configuring `kedro run` arguments

The extensive list of CLI options for a `kedro run` is available [here](./06_pipelines.md#modifying-a-kedro-run). Instead of specifying all the command line options to a `kedro run` via the CLI, you can specify a config file that contains the arguments, say `config.yml` and run:

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

> *Note*: If you pass both a configuration file and an option that clashes with one inside the configuration file, the provided option will override the configuration file.
