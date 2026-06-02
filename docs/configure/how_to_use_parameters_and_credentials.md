# How to work with parameters and credentials

This guide shows you how to work with parameters and credentials in your Kedro project.

## On this page

- [How to use parameters in your pipeline](#how-to-use-parameters-in-your-pipeline)
- [How to load parameters in code](#how-to-load-parameters-in-code)
- [How to specify parameters at runtime](#how-to-specify-parameters-at-runtime)
- [How to validate parameters](#how-to-validate-parameters)
- [How to load credentials in code](#how-to-load-credentials-in-code)
- [How to load credentials through environment variables](#how-to-load-credentials-through-environment-variables)
- [How to work with AWS credentials](#how-to-work-with-aws-credentials)

## How to use parameters in your pipeline

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

[Parameters can then be used on their own or fed in as function inputs](parameters_and_credentials_explanation.md#how-parameters-work).

## How to specify parameters at runtime

Kedro also allows you to specify runtime parameters for the `kedro run` CLI command. Use the `--params` command line option and provide a comma-separated list of key-value pairs. Kedro adds these values to [kedro.framework.context.KedroContext][] parameters and makes them available to pipeline nodes.

Each key-value pair is split on the first equals sign. The following example is a valid command:

```bash
kedro run --params=param_key1=value1,param_key2=2.0
```
Values provided in the CLI take precedence and overwrite parameters specified in configuration files. By default, runtime parameters merge destructively, meaning that any configuration for that key **besides the runtime value** is discarded.
[This section describes how to change the merging strategy](how_to_configure_project.md#how-to-change-the-merge-strategy-used-by-omegaconfigloader).

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
    To **override parameters and other configurations**, such as catalog entries or file paths, or to specify upfront that certain parameters must be set at runtime, use `$runtime_params` with the `OmegaConfigLoader`. Introduced in Kedro `0.18.14`, this feature allows dynamic overrides of various configuration types using the `--params` CLI option. Use it when you need to switch data sources or adjust runtime settings. [Learn more about `$runtime_params`.](how_to_use_templating.md#how-to-override-configuration-with-runtime-parameters-with-the-omegaconfigloader)

## How to validate parameters

Kedro can validate parameters from your YAML configuration against type hints on your node functions. When a node declares a [Pydantic model](https://docs.pydantic.dev/latest/) or [dataclass](https://docs.python.org/3/library/dataclasses.html) type hint for a `params:` input, Kedro automatically converts the raw dictionary into a validated, typed object before any node runs.

This feature is **opt-in**: add a type hint to enable validation for that parameter, or leave it untyped to keep the existing behaviour.

### Supported types

Parameter validation supports two kinds of typed objects:

- **Pydantic models** (v2+): Full validation with field constraints, nested models, and custom validators. Requires `pip install "kedro[pydantic]"`.
- **Dataclasses**: Basic type checking using Python's built-in `dataclasses` module. No extra dependencies needed.

!!! note
    You can use either Pydantic models or dataclasses. You do not need both.

Raw values (`int`, `str`, `float`, and others) are passed through unchanged with no validation applied.

### How validation works

1. When you execute a Kedro run or access `context.params` directly, Kedro loads your `parameters.yml` as a dictionary.
2. Kedro inspects the signatures of all registered pipeline node functions. For any `params:` input with a Pydantic model or dataclass type hint, it records the expected type.
3. For each typed parameter, Kedro converts the raw dictionary into the declared type using `model_validate` (Pydantic) or keyword-argument instantiation (dataclasses).
4. If any conversion fails, Kedro raises a `ParameterValidationError` with details about the failure, before any node runs.
5. Validated parameters are cached, so repeated access to `context.params` does not re-validate.

### Fail-fast behaviour

Validation runs before any node executes. This **fail-fast** behaviour means configuration errors are caught early, not halfway through a long pipeline run.

### Pydantic vs. dataclasses

Pydantic models provide richer validation: field constraints (`ge`, `le`, `gt`, `lt`), custom validators, nested model support, and detailed error messages. Dataclasses check that required fields are present and can be instantiated from the dictionary, but do not enforce value constraints. Use Pydantic models if you need validation beyond basic type checking.

### Conflicting types across pipelines

If two pipelines declare different types for the same parameter key, Kedro logs a warning and uses the type from the last pipeline processed. The run still executes without error. For example, `params:training` typed as `TrainingParamsA` in one pipeline and `TrainingParamsB` in another triggers this warning. Avoid this by using consistent types for the same parameter key.

### Optional type hints

If a parameter is optional, you can use `Optional[Model]` or `Model | None`. Kedro unwraps the optional and validates against the inner type:

```python
from __future__ import annotations

from pydantic import BaseModel


class TrainingParams(BaseModel):
    learning_rate: float
    epochs: int


def train(data, params: TrainingParams | None):
    ...
```

Kedro validates `params` against `TrainingParams` even though the hint is `TrainingParams | None`.

### Known limitations

- **Validates across all pipelines**: Kedro inspects all registered pipelines for type hints, regardless of which pipeline you are running. This means a validation error in an unrelated pipeline can block your run. See [GitHub issue #5443](https://github.com/kedro-org/kedro/issues/5443) for progress on scoping validation to the target pipeline.
- **Pydantic v1 is not supported**: The validation framework uses `model_validate`, which is a Pydantic v2+ API. If your project uses Pydantic v1, you need to upgrade to v2.
- **Dataset inputs are not validated**: Validation applies to parameters loaded through `params:` or `parameters`. It does not cover dataset inputs.
- **Multi-type unions are not validated**: Union type hints with multiple non-None types (for example `ModelA | ModelB`) are skipped and no validation is applied. `Optional[Model]` (one model type plus `None`) is unwrapped and validated. Support for multi-type unions may be added in a future release.

### Set up a basic Pydantic model

Define a Pydantic model for your parameters:

```python
# src/<package_name>/parameters.py
from pydantic import BaseModel, Field


class ModelOptions(BaseModel):
    test_size: float = Field(ge=0.1, le=0.5)
    random_state: int = Field(ge=0)
```

Add the type hint to your node function:

```python
# src/<package_name>/pipelines/data_science/nodes.py
from sklearn.model_selection import train_test_split

from <package_name>.parameters import ModelOptions


def split_data(data, params: ModelOptions):
    # params is a validated ModelOptions instance, not a dict
    X_train, X_test = train_test_split(
        data, test_size=params.test_size, random_state=params.random_state
    )
    return X_train, X_test
```

Define the pipeline as usual. No changes needed:

```python
from kedro.pipeline import node, pipeline


def create_pipeline(**kwargs):
    return pipeline(
        [
            node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "X_test"],
            ),
        ]
    )
```

Your `parameters.yml` stays the same:

```yaml
# conf/base/parameters.yml
model_options:
  test_size: 0.2
  random_state: 3
```

When you run `kedro run`, Kedro validates `model_options` against the `ModelOptions` schema. If `test_size` is outside the `0.1`-`0.5` range, Kedro raises an error before any node executes.

### Use field constraints

Use Pydantic's `Field` to add validation constraints:

```python
from pydantic import BaseModel, Field


class TrainingParams(BaseModel):
    learning_rate: float = Field(gt=0, le=1, description="Must be between 0 and 1")
    epochs: int = Field(ge=1, le=1000)
    dropout: float = Field(ge=0, le=1, default=0.5)
```

See the [Pydantic field documentation](https://docs.pydantic.dev/latest/concepts/fields/) for the full list of constraints.

### Use nested models

If your configuration has nested structure, define nested Pydantic models:

```python
from pydantic import BaseModel


class OptimizerConfig(BaseModel):
    name: str
    learning_rate: float


class TrainingConfig(BaseModel):
    epochs: int
    optimizer: OptimizerConfig


def train(data, params: TrainingConfig):
    # params.optimizer is an OptimizerConfig instance, not a dict
    opt = create_optimizer(params.optimizer.name, lr=params.optimizer.learning_rate)
    ...
```

```yaml
training:
  epochs: 10
  optimizer:
    name: adam
    learning_rate: 0.001
```

Nested sub-models are preserved as typed objects. `params.optimizer` is an `OptimizerConfig` instance with attribute access and its own validation.

### Use custom validators

You can use Pydantic's `@field_validator` for custom validation logic:

```python
from pydantic import BaseModel, field_validator


class SplitParams(BaseModel):
    test_size: float
    val_size: float

    @field_validator("test_size", "val_size")
    @classmethod
    def must_be_fraction(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("must be between 0 and 1")
        return v
```

See the [Pydantic validators documentation](https://docs.pydantic.dev/latest/concepts/validators/) for more patterns.

### Use dataclasses

You can use Python's built-in `dataclasses` instead of Pydantic:

```python
from dataclasses import dataclass


@dataclass
class EvalConfig:
    metric: str
    threshold: float


def evaluate_model(model, params: EvalConfig):
    score = compute_score(model, metric=params.metric)
    if score < params.threshold:
        raise ValueError(f"Model score {score} below threshold {params.threshold}")
```

```yaml
eval:
  metric: accuracy
  threshold: 0.85
```

!!! note
    Dataclasses do not have built-in field validation like Pydantic. Kedro instantiates the dataclass from the dictionary and checks that the required fields are present, but it does not enforce constraints like `ge`, `le`, or custom validators. Use Pydantic models if you need richer validation.

### Use multiple typed parameters in one node

A node can have multiple `params:` inputs, each with its own type:

```python
def train_and_evaluate(data, training: TrainingParams, eval_config: EvalConfig):
    ...
```

```python
node(
    func=train_and_evaluate,
    inputs=["data", "params:training", "params:eval"],
    outputs="result",
)
```

### Mix typed and untyped parameters

You can use typed parameters alongside untyped ones in the same project. Nodes without type hints receive plain dictionaries as before:

```python
# This node gets a validated Pydantic model
def train(data, params: TrainingParams):
    ...

# This node gets a plain dict, no validation
def preprocess(data, params):
    lr = params["learning_rate"]
    ...
```

### Use runtime parameters with validation

Runtime parameters specified with `--params` are merged into the configuration before validation runs:

```bash
kedro run --params="training.learning_rate:0.1"
```

The merged value is validated against the type hint, so invalid runtime overrides are caught the same way as invalid YAML values.

### Read validation error messages

When validation fails, Kedro raises a `ParameterValidationError` with details about which field failed and why:

```yaml
# conf/base/parameters.yml
model_options:
  test_size: 5.0  # exceeds le=0.5 constraint
  random_state: 3
```

```
ParameterValidationError: Parameter validation failed:
- Parameter 'model_options': Failed to instantiate ModelOptions for parameter 'model_options':
  1 validation error for ModelOptions
  test_size
    Input should be less than or equal to 0.5 [type=less_than_equal, ...]
```

The error includes the parameter key name and the full Pydantic validation output, making it straightforward to identify which field has an invalid value.

## How to load credentials in code

Credentials configuration can be loaded the same way as any other project configuration using the configuration loader class `OmegaConfigLoader`.


```python
from pathlib import Path

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

# Substitute <project_root> with the root folder for your project
conf_path = str(Path(<project_root>) / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)
credentials = conf_loader["credentials"]
```

This loads configuration files from `conf/base` and `conf/local` whose filenames start with `credentials`, or that are located inside a folder with a name that starts with `credentials`.

Calling `conf_loader[key]` in the example above throws a `MissingConfigException` error if no configuration files match the given key. But if this is a valid workflow for your application, you can handle it as follows:

```python
from pathlib import Path

from kedro.config import OmegaConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(Path(<project_root>) / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

try:
    credentials = conf_loader["credentials"]
except MissingConfigException:
    credentials = {}
```

!!! note
    The `kedro.framework.context.KedroContext` class uses the approach above to load project credentials.

## How to load credentials through environment variables

The [kedro.config.OmegaConfigLoader][] enables you to load credentials from environment variables. To achieve this you have to use the [kedro.config.OmegaConfigLoader][] and the `omegaconf` [`oc.env` resolver](https://omegaconf.readthedocs.io/en/2.3_branch/custom_resolvers.html#oc-env).
You can use the `oc.env` resolver to access credentials from environment variables in your `credentials.yml`:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: ${oc.env:AWS_ACCESS_KEY_ID}
    aws_secret_access_key: ${oc.env:AWS_SECRET_ACCESS_KEY}
```

!!! note
    You can use this resolver solely in `credentials.yml`, not in catalog or parameter files. This restriction discourages using environment variables for anything other than credentials.

## How to work with AWS credentials

When you work with AWS credentials on datasets, you are not required to store AWS credentials in the project configuration files. Instead, you can specify them using environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, optionally, `AWS_SESSION_TOKEN`. See the [official AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.
