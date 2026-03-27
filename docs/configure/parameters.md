# Parameters
Project parameters in Kedro are defined inside the `conf` folder in a file that has a filename starting with `parameters`, or are located inside a folder with name starting with `parameters`.
By default, in a new Kedro project, parameters are defined in the `parameters.yml` file, which is located in the project's `conf/base` directory. This file contains a dictionary of key-value pairs, where each key is a parameter name and each value is the corresponding parameter value.
These parameters can serve as input to nodes and are used when running the pipeline. By using parameters, you can make your Kedro pipelines more flexible and easier to configure, since you can change the behaviour of your nodes by modifying the `parameters.yml` file.

## How to use parameters
If you have a group of parameters that determine the hyperparameters of your model, define them in a single location such as `conf/base/parameters.yml`. Keeping everything together reduces the chances of missing an update elsewhere in the codebase.

```yaml
step_size: 1
learning_rate: 0.01
```

You can now use the `params:` prefix to reference these parameters in the `node` definition:

```python
def increase_volume(volume, step):
    return volume + step


# in pipeline definition
Node(
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
Node(
    func=train_model,
    inputs=["input_data", "params:model_params"],
    outputs="output_data",
)
```

You can also pass `parameters` to the node inputs and access the entire collection of values inside the node function.

```python
def increase_volume(volume, params):
    step = params["step_size"]
    return volume + step


# in pipeline definition
Node(
    func=increase_volume, inputs=["input_volume", "parameters"], outputs="output_volume"
)
```

In both cases, Kedro adds the parameters to the Data Catalog as `MemoryDataset`s.


## How to load parameters in code

Parameters project configuration can be loaded by the configuration loader class, which is `OmegaConfigLoader` by default.

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)
parameters = conf_loader["parameters"]
```

This loads configuration files from any subdirectories in `conf` that have a filename starting with `parameters`, or are located inside a folder with name starting with `parameters`.

Calling `conf_loader[key]` in the example above will throw a `MissingConfigException` error if no configuration files match the given key. But if this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import OmegaConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

try:
    parameters = conf_loader["parameters"]
except MissingConfigException:
    parameters = {}
```

!!! note
    The `kedro.framework.context.KedroContext` class uses the approach above to load project parameters.

[Parameters can then be used on their own or fed in as function inputs](#how-to-use-parameters).

## How to specify parameters at runtime

Kedro also allows you to specify runtime parameters for the `kedro run` CLI command. Use the `--params` command line option and provide a comma-separated list of key-value pairs. Kedro adds these values to [kedro.framework.context.KedroContext][] parameters and makes them available to pipeline nodes.

Each key-value pair is split on the first equals sign. The following example is a valid command:

```bash
kedro run --params=param_key1=value1,param_key2=2.0
```
Values provided in the CLI take precedence and overwrite parameters specified in configuration files. By default, runtime parameters merge destructively, meaning that any configuration for that key **besides the runtime value** is discarded.
[This section describes how to change the merging strategy](advanced_configuration.md#how-to-change-the-merge-strategy-used-by-omegaconfigloader).

For example, if you have the following parameters in your `base` and `local` environments:

```yaml
# base/parameters.yml
model_options:
  model_params:
    learning_date: "2023-11-01"
    training_date: "2023-11-01"
    data_ratio: 14

data_options:
  step_size: 123123
```

```yaml
# local/parameters.yml
features:
    rate: 123
```

And you provide the following parameter at runtime:

```bash
kedro run --params="model_options.model_params.training_date=2011-11-11"
```

The final merged result will be:
```yaml
model_options:
  model_params:
    training_date: "2011-11-11"

data_options:
  step_size: 123123

features:
    rate: 123
```

* Parameter keys are _always_ treated as strings.
* Parameter values are converted to a float or an integer number if the corresponding conversion succeeds; otherwise, they are also treated as string.

If any extra parameter key or value contains spaces, wrap the whole option contents in quotes:

```bash
kedro run --params="key1=value with spaces,key2=value"
```

Since key-value pairs are split on the first equals sign, values can contain equals signs, but keys cannot.


!!! note
    To **override parameters and other configurations**, such as catalog entries or file paths, or to specify upfront that certain parameters must be set at runtime, use `$runtime_params` with the `OmegaConfigLoader`. Introduced in Kedro `0.18.14`, this feature allows dynamic overrides of various configuration types using the `--params` CLI option. Use it when you need to switch data sources or adjust runtime settings. [Learn more about `$runtime_params`.](advanced_configuration.md#how-to-override-configuration-with-runtime-parameters-with-the-omegaconfigloader)

## Parameter validation with type hints

Kedro can automatically validate your parameters against type-annotated node functions. If you add a [Pydantic model](https://docs.pydantic.dev/latest/) or [dataclass](https://docs.python.org/3/library/dataclasses.html) type hint to a `params:` input, Kedro converts the raw YAML dictionary into a validated, typed object before any node runs.

This is entirely **opt-in**. Projects without type hints continue to work as before.

```python
from pydantic import BaseModel, Field


class ModelOptions(BaseModel):
    test_size: float = Field(ge=0.1, le=0.5)
    random_state: int = Field(ge=0)


def split_data(data, params: ModelOptions):
    # params is a validated ModelOptions instance, not a dict
    X_train, X_test = train_test_split(
        data, test_size=params.test_size, random_state=params.random_state
    )
    return X_train, X_test
```

```yaml
# conf/base/parameters.yml
model_options:
  test_size: 0.2
  random_state: 3
```

If validation fails (for example, `test_size: 5.0` exceeds the `le=0.5` constraint), Kedro raises an error before any node runs, with a clear message showing which field failed and why.

For more details, including dataclass support, nested models, and advanced usage, see the [Parameter validation reference](parameter_validation.md).
