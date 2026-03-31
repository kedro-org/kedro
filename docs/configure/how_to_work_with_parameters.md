# Work with Parameters

## Define parameters

Create `conf/base/parameters.yml`:

```yaml
step_size: 1
learning_rate: 0.01
```

Or use nested structures:

```yaml
model_params:
  learning_rate: 0.01
  test_data_ratio: 0.2
  number_of_train_iterations: 10000
```

Organize parameters across multiple files. All matching `parameters*` are merged:

```
conf/base/
├── parameters.yml
├── parameters_training.yml
└── parameters_data_processing.yml
```

## Use parameters in pipeline nodes

**Individual parameter:**

```python
def increase_volume(volume, step):
    return volume + step

# In pipeline
node(
    func=increase_volume,
    inputs=["input_volume", "params:step_size"],
    outputs="output_volume",
)
```

**Parameter group:**

```python
def train_model(data, model):
    lr = model["learning_rate"]
    test_data_ratio = model["test_data_ratio"]
    # ...

# In pipeline
node(
    func=train_model,
    inputs=["input_data", "params:model_params"],
    outputs="output_data",
)
```

**All parameters:**

```python
def process_data(data, parameters):
    step = parameters["step_size"]
    # ...

# In pipeline
node(
    func=process_data,
    inputs=["input_data", "parameters"],
    outputs="output_data",
)
```

## Load parameters in code

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)
parameters = conf_loader["parameters"]
```

Handle cases where parameters might not exist:

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
    The `KedroContext` class uses this approach to load project parameters.

## Override parameters at runtime

```bash
kedro run --params="learning_rate=0.05"
kedro run --params="learning_rate=0.05,step_size=2"
kedro run --params="model_params.learning_rate=0.05"
```

- Values are converted to `float`/`int` if possible, otherwise `string`
- Keys are always strings
- Quote values with spaces: `--params="key=value with spaces"`
- Values can contain `=`, but keys cannot

### Merge behavior

By default, runtime parameters merge **destructively** - the entire key is replaced:

```yaml
# base/parameters.yml
model_options:
  model_params:
    learning_date: "2023-11-01"
    training_date: "2023-11-01"
    data_ratio: 14
```

```bash
kedro run --params="model_options.model_params.training_date=2011-11-11"
```

Result - only `training_date` remains, other keys are discarded:

```yaml
model_options:
  model_params:
    training_date: "2011-11-11"  # Only this remains
```

To change this behavior, see [how to change merge strategies](./how_to_configure_project.md#change-merge-strategies).

---

## Require parameters at runtime

Specify that parameters must be provided at runtime using `${runtime_params:}`:

```yaml
# conf/base/parameters.yml
model_options:
  random_state: "${runtime_params:seed}"           # Required
  learning_rate: "${runtime_params:lr, 0.01}"      # Optional with default
```

```bash
kedro run --params="seed=42,lr=0.05"
```

See [runtime parameter overrides](./how_to_use_templating.md#override-configuration-with-runtime-parameters) for more details.
