# Parameter validation

Kedro can validate parameters from your YAML configuration against type hints on your node functions. When a node declares a [Pydantic model](https://docs.pydantic.dev/latest/) or [dataclass](https://docs.python.org/3/library/dataclasses.html) type hint for a `params:` input, Kedro automatically converts the raw dictionary into a validated, typed object before any node runs.

This feature is **opt-in**: add a type hint to enable validation for that parameter, or leave it untyped to keep the existing behaviour.

## Concepts

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

---

## How to validate parameters in Kedro

There are two approaches to parameter validation:

- **With Pydantic models**: Provides field constraints, nested model support, and custom validators. Requires installing Pydantic (`pip install "kedro[pydantic]"`).
- **With dataclasses**: Uses Python's built-in `dataclasses` module with no extra dependencies, but without constraint validation.

The sections below cover Pydantic first, then [dataclasses](#use-dataclasses).

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
