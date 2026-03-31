# Templating with OmegaConfigLoader

Templating, also known as variable interpolation, allows you to reference values from other parts of your configuration using the `${...}` syntax. This powerful feature helps you keep your configuration DRY (Don't Repeat Yourself), maintain consistency, and manage values centrally.

## Variable interpolation concepts

Variable interpolation lets you define a value once and reference it multiple times throughout your configuration:

```yaml
# Define once
database:
  host: prod-db.example.com
  port: 5432

# Reference multiple times
raw_data_connection: "postgresql://${database.host}:${database.port}/raw"
processed_data_connection: "postgresql://${database.host}:${database.port}/processed"
```

When Kedro loads this configuration, it resolves the `${...}` placeholders by replacing them with the actual values. This is particularly useful for:

- **Avoiding duplication**: Define common values once
- **Maintaining consistency**: Change a value in one place, update everywhere
- **Building complex values**: Compose strings or structures from simpler parts
- **Environment-specific values**: Reference different values per environment

OmegaConfigLoader handles interpolation automatically when loading configuration, so resolved values are immediately available to your code.

## Scoped vs global variables

OmegaConfigLoader supports two scopes for variable interpolation: scoped (within a configuration type) and global (across configuration types).

### Scoped variables

Scoped variables are only available within the same configuration type and environment. For example, variables defined in parameter files can only reference other values within parameter files in the same environment.

**Parameters example:**

```yaml
# conf/base/parameters.yml
step_size: 1
batch_size: 32

# conf/base/parameters_model.yml
model_options:
  steps: ${step_size}      # References value from parameters.yml
  batch: ${batch_size}     # Both files must match "parameters*" pattern
```

This works because both files match the `parameters*` pattern and are in the same environment (`base`).

**Catalog example:**

```yaml
# conf/base/catalog_variables.yml
_file_format: "parquet"       # Must start with _ for catalog
_base_path: "s3://my-bucket/data"

# conf/base/catalog.yml
raw_data:
  type: spark.SparkDataset
  filepath: "${_base_path}/raw/data.${_file_format}"
  file_format: ${_file_format}
```

For catalog files, template variables must start with an underscore `_`. This is required because of how catalog entries are validated. The underscore marks these as template values rather than actual dataset definitions.

**Why different environments don't share scoped variables:**

```yaml
# conf/base/parameters.yml
base_value: 100

# conf/local/parameters.yml
local_value: ${base_value}   # ❌ Won't work - different environments
```

Scoped variables are limited to their environment to keep configuration predictable and avoid unexpected dependencies between environments.

### Global variables

Global variables, available since Kedro 0.18.13, can be shared across different configuration types and environments. This is useful when you need the same value in both your parameters and your catalog.

```yaml
# conf/base/globals.yml
bucket_name: "my-s3-bucket"
file_format: "parquet"
```

```yaml
# conf/base/parameters.yml
data_settings:
  storage: "${globals:bucket_name}"   # Reference global variable
  format: "${globals:file_format}"
```

```yaml
# conf/base/catalog.yml
raw_data:
  type: spark.SparkDataset
  filepath: "s3://${globals:bucket_name}/raw/data"
  file_format: ${globals:file_format}
```

Global variables are defined in files named `globals.yml` (or matching the pattern `globals*`) and accessed using the `${globals:key}` resolver syntax.

## Understanding resolvers

Resolvers are functions that compute or retrieve values dynamically when configuration is loaded. The `${...}` syntax invokes these resolvers.

### Basic interpolation

The simplest form is direct value reference:

```yaml
value: 42
reference: ${value}   # Resolves to 42
```

### Nested paths

Access nested values using dot notation:

```yaml
database:
  connection:
    host: "localhost"
    port: 5432

connection_string: "${database.connection.host}:${database.connection.port}"
# Resolves to: "localhost:5432"
```

### Default values

Provide a fallback value if the key doesn't exist:

```yaml
host: "${custom_host, localhost}"   # Use localhost if custom_host not defined
```

### Built-in resolvers

OmegaConf provides several built-in resolvers:

**`oc.env`**: Load values from environment variables (enabled for credentials only by default)

```yaml
# conf/local/credentials.yml
api_key: ${oc.env:API_KEY}
```

**`oc.select`**: Select a value with a default fallback

```yaml
environment: ${oc.select:DEPLOY_ENV, development}
```

See the [OmegaConf documentation](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#built-in-resolvers) for all built-in resolvers.

### Custom resolvers

You can create custom resolvers to compute values dynamically. For example, to automatically use today's date in your configuration:

```python
# src/my_project/settings.py
from datetime import date

CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "today": lambda: date.today().isoformat(),
        "add": lambda *values: sum(values),
    }
}
```

```yaml
# conf/base/parameters.yml
run_date: "${today:}"              # Resolves to current date, e.g., "2024-03-15"
total_budget: "${add:100,200,300}" # Resolves to 600
```

Custom resolvers are particularly useful for:
- Generating timestamps or UUIDs
- Performing calculations
- Accessing non-primitive Python types
- Implementing custom logic

See [how to create custom resolvers](./how_to_use_templating.md#create-custom-resolvers-for-dynamic-values) for detailed examples.

## Runtime parameter resolution

Runtime parameter resolution, available since Kedro 0.18.14, lets you mark configuration values as overridable from the command line. This is useful when you want to:

- Indicate that certain values should be provided at runtime
- Provide defaults that can be overridden
- Make your configuration more flexible without hardcoding values

```yaml
# conf/base/parameters.yml
model_options:
  random_state: "${runtime_params:random_seed}"
  learning_rate: "${runtime_params:lr, 0.01}"   # With default value
```

```bash
# Override at runtime
kedro run --params="random_seed=42,lr=0.001"
```

The `runtime_params` resolver looks for values passed via the `--params` CLI option. If not provided, it uses the default value (if specified) or raises an error.

### Why globals cannot be overridden by runtime_params

The `runtime_params` resolver is intentionally designed not to override `globals` configuration. This prevents unexplicit overrides and simplifies parameter resolution.

```yaml
# conf/base/globals.yml
max_iterations: 1000

# conf/base/parameters.yml
iterations: "${runtime_params:max_iterations}"   # ✓ Can override via CLI

# This pattern does NOT override globals:
iterations: "${max_iterations}"                   # ✗ Always uses global value
```

Globals have a single entry point (the YAML file) to keep configuration predictable and traceable.

### Combining approaches

You can use globals as defaults for runtime parameters:

```yaml
# conf/base/globals.yml
default_learning_rate: 0.01

# conf/base/parameters.yml
model_options:
  learning_rate: "${runtime_params:lr, ${globals:default_learning_rate}}"
```

This pattern provides:
1. A team-wide default in `globals.yml` (version controlled)
2. The ability to override at runtime for experiments
3. Clear documentation of what can be overridden

## When to use each templating approach

Choose your templating approach based on your needs:

| Use Case | Approach | Example |
|----------|----------|---------|
| Share values within parameters | Scoped interpolation | `${param_name}` |
| Share values within catalog | Scoped interpolation with `_` | `${_catalog_var}` |
| Share values across config types | Global variables | `${globals:shared_value}` |
| Override at runtime | Runtime params | `${runtime_params:key,default}` |
| Load from environment variables | Built-in resolver | `${oc.env:VAR_NAME}` |
| Dynamic computation | Custom resolver | `${today:}` or `${add:1,2,3}` |

**General guidelines:**

- Start with scoped interpolation for simple cases
- Use globals when you need to share values between parameters and catalog
- Use runtime params for values that change frequently during experimentation
- Use custom resolvers for computed or dynamic values
- Use environment variables (oc.env) only for credentials

## Where to go next

Now that you understand templating concepts, you can:

- Learn [how to template values within configuration files](./how_to_use_templating.md#template-values-within-configuration-files)
- Discover [how to share variables across configurations with globals](./how_to_use_templating.md#share-variables-across-configurations-with-globals)
- Explore [how to create custom resolvers](./how_to_use_templating.md#create-custom-resolvers-for-dynamic-values)
- See [how to override configuration with runtime parameters](./how_to_use_templating.md#override-configuration-with-runtime-parameters)
- Check the [Resolver Syntax Quick Reference](./reference_resolver_syntax.md) for syntax details
