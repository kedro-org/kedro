# Parameters and Credentials

Parameters and credentials are two types of configuration values that serve different purposes in your Kedro project. Understanding when to use each helps you build secure, maintainable pipelines.

## What are parameters

Parameters are configuration values that control the behavior of your data pipeline. They represent settings that you might want to adjust between runs or experiments, such as:

- Model hyperparameters (learning rate, number of epochs, regularization strength)
- Data processing settings (test/train split ratio, feature selection thresholds)
- Business logic values (date ranges, category filters, aggregation rules)
- Pipeline behavior flags (enable debugging, skip certain steps)

Parameters are defined in files that match the pattern `parameters*` within your `conf/` directory. By default, new Kedro projects include `conf/base/parameters.yml`.

### Why use parameters

Storing values as parameters rather than hardcoding them in your pipeline code offers several advantages:

**Experimentation flexibility**: Easily test different model configurations without editing code:
```bash
# Try different learning rates
kedro run --params="learning_rate=0.01"
kedro run --params="learning_rate=0.001"
```

**Environment adaptation**: Use different parameter values for development vs production:
```yaml
# conf/base/parameters.yml
data_sample_size: 1000  # Small sample for development

# conf/prod/parameters.yml
data_sample_size: 1000000  # Full dataset for production
```

**Reproducibility**: Track parameter values in version control to reproduce results:
```yaml
# parameters.yml committed to git
model_params:
  random_state: 42
  n_estimators: 100
```

**Collaboration**: Share settings with your team without everyone needing to understand the code.

## How parameters integrate with pipelines

When you define parameters in configuration files, Kedro automatically makes them available to your pipeline nodes. Parameters are added to the Data Catalog as `MemoryDataset` objects, which means you can access them just like any other dataset.

There are three ways to use parameters in your nodes:

### 1. Individual parameters

Reference a specific parameter using the `params:` prefix:

```python
# node function
def increase_volume(volume, step):
    return volume + step

# pipeline definition
node(
    func=increase_volume,
    inputs=["input_volume", "params:step_size"],
    outputs="output_volume",
)
```

```yaml
# conf/base/parameters.yml
step_size: 1
```

### 2. Nested parameter groups

Access a group of related parameters as a dictionary:

```python
# node function
def train_model(data, model_params):
    lr = model_params["learning_rate"]
    test_ratio = model_params["test_data_ratio"]
    iterations = model_params["number_of_train_iterations"]
    # ... training logic

# pipeline definition
node(
    func=train_model,
    inputs=["input_data", "params:model_params"],
    outputs="trained_model",
)
```

```yaml
# conf/base/parameters.yml
model_params:
  learning_rate: 0.01
  test_data_ratio: 0.2
  number_of_train_iterations: 10000
```

### 3. All parameters

Access the entire parameter collection:

```python
# node function
def process_data(data, parameters):
    step = parameters["step_size"]
    threshold = parameters["threshold"]
    # ... processing logic

# pipeline definition
node(
    func=process_data,
    inputs=["input_data", "parameters"],
    outputs="processed_data",
)
```

This approach gives your node access to all parameters defined in your configuration.

## What are credentials

Credentials are sensitive configuration values that should never be committed to version control. They represent secrets that provide access to protected resources:

- Database passwords
- API keys and tokens
- Cloud storage access keys
- OAuth secrets
- Encryption keys

Credentials are defined in files that match the pattern `credentials*` within your `conf/` directory.

## Security model for credentials

Kedro implements several safeguards to protect your credentials:

### Git ignore by default

Any file in the `conf/` directory (and its subdirectories) that contains the word "credentials" in its filename is automatically ignored by Git. This is configured in the `.gitignore` file created with every new Kedro project:

```
# .gitignore (created automatically)
**/credentials*
```

This prevents accidental commits of sensitive information.

### Local environment storage

Credentials should always be stored in the `local` environment, which is also excluded from version control:

```
conf/local/
└── credentials.yml      # Never committed to git
```

The `conf/local/` folder itself is gitignored, providing an additional layer of protection.

### Environment variable alternative

For production deployments and CI/CD pipelines, you can load credentials from environment variables instead of files. This is the recommended approach for cloud deployments:

```yaml
# conf/local/credentials.yml
dev_database:
  username: ${oc.env:DB_USERNAME}
  password: ${oc.env:DB_PASSWORD}
```

See [how to use environment variables for credentials](./how_to_manage_credentials.md#use-environment-variables-for-credentials) for details.

## Why separate credentials from parameters

While both credentials and parameters are configuration values, they have fundamentally different security requirements:

| Aspect | Parameters | Credentials |
|--------|-----------|-------------|
| **Version control** | Committed to git | Never committed |
| **Sharing** | Shared with team | Individual or system-specific |
| **Visibility** | Can be logged/displayed | Must remain hidden |
| **Environment** | Usually in `base` or custom envs | Always in `local` |
| **Change frequency** | Modified for experiments | Rarely changed |

Keeping them separate makes it easier to follow security best practices and reduces the risk of accidentally exposing sensitive information.

## Version control considerations

When working with configuration in a team:

**Do commit:**
- Parameter files in `conf/base/`
- Parameter files in custom environments (`conf/prod/`, `conf/staging/`)
- Example credential file structures (with dummy values)
- Documentation about which credentials are needed

**Don't commit:**
- Anything in `conf/local/`
- Any file with real credentials or secrets
- Personal development settings
- Sensitive file paths or system information

A good practice is to include a `conf/local/credentials.yml.example` file with dummy values:

```yaml
# conf/local/credentials.yml.example (committed to git)
# Copy this to conf/local/credentials.yml and fill in real values

dev_database:
  username: "your_username_here"
  password: "your_password_here"

api_keys:
  service_name: "your_api_key_here"
```

This helps new team members understand what credentials they need to configure without exposing actual secrets.

## Where to go next

Now that you understand parameters and credentials, you can:

- Learn [how to define and use parameters](./how_to_work_with_parameters.md) in your pipelines
- Discover [how to manage credentials securely](./how_to_manage_credentials.md)
- Explore [templating with OmegaConfigLoader](./04_templating_with_omegaconfigloader.md) for advanced configuration
- Follow the [Quick Start guide](./quick_start.md) to configure your first pipeline
