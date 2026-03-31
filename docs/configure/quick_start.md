# Quick Start: Configuration

This guide will get you up and running with Kedro configuration in 5 minutes using the spaceflights tutorial project. You'll learn how to define parameters, use them in your pipeline, and add credentials securely.

## Prerequisites

This guide assumes you have:

- Completed the [spaceflights tutorial setup](../tutorials/tutorial_template.md) to create the spaceflights project
- The spaceflights project created and dependencies installed
- Basic familiarity with YAML syntax

If you haven't set up the spaceflights project yet, navigate to your working directory and run:

```bash
uvx kedro new --starter spaceflights-pandas --name spaceflights
cd spaceflights
uv sync
```

## What this guide covers

This guide explains:

- How to define parameters in configuration files
- How to use parameters in your pipeline nodes
- How to override parameters at runtime
- How to store credentials securely

## Explore the existing parameters

The spaceflights starter already includes parameter files. Let's examine them.

Open `conf/base/parameters_data_science.yml`:

```yaml
model_options:
  test_size: 0.2
  random_state: 3
  features:
    - engines
    - passenger_capacity
    - crew
    - d_check_complete
    - moon_clearance_complete
    - iata_approved
    - company_rating
    - review_scores_rating
```

These parameters control model training in the data science pipeline. Let's see how they're used.

## Use parameters in nodes

Parameters are accessed in pipeline nodes using the `params:` prefix. The spaceflights project demonstrates this in the data science pipeline.

Open `src/spaceflights/pipelines/data_science/nodes.py` and find the `split_data` function:

```python
def split_data(data: pd.DataFrame, parameters: dict) -> tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data: Data containing features and target.
        parameters: Parameters defined in parameters/data_science.yml.
    Returns:
        Split data.
    """
    X = data[parameters["features"]]
    y = data["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )
    return X_train, X_test, y_train, y_test
```

The function receives a `parameters` dictionary containing all the values from `model_options`.

Now open `src/spaceflights/pipelines/data_science/pipeline.py` to see how the node uses these parameters:

```python
from kedro.pipeline import Node, Pipeline

from .nodes import split_data, train_model, evaluate_model


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
                name="split_data_node",
            ),
            Node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
            Node(
                func=evaluate_model,
                inputs=["regressor", "X_test", "y_test"],
                outputs="metrics",
                name="evaluate_model_node",
            ),
        ]
    )
```

Notice the `inputs=["model_input_table", "params:model_options"]` line. The `params:model_options` syntax tells Kedro to load the `model_options` parameter group and pass it to the function.

## Test parameters with your pipeline

Run the data science pipeline to see parameters in action:

```bash
kedro run --pipeline=data_science
```

You should see output showing the pipeline executing successfully:

```bash
[INFO] Loading data from 'model_input_table' (ParquetDataset)...
[INFO] Running node: split_data_node: split_data([model_input_table,params:model_options]) -> [X_train,X_test,y_train,y_test]
[INFO] Saving data to 'X_train' (MemoryDataset)...
[INFO] Running node: train_model_node: train_model([X_train,y_train]) -> [regressor]
[INFO] Running node: evaluate_model_node: evaluate_model([regressor,X_test,y_test]) -> [metrics]
[INFO] Model has a coefficient R^2 of 0.462 on test data.
[INFO] Pipeline execution completed successfully.
```

## Override parameters at runtime

Want to experiment with different model settings without editing files? Override parameters at runtime:

```bash
kedro run --pipeline=data_science --params="model_options.test_size=0.3"
```

This runs the data science pipeline with a 30% test split instead of the default 20%.

You can override multiple parameters:

```bash
kedro run --pipeline=data_science --params="model_options.test_size=0.3,model_options.random_state=42"
```

Runtime parameters take precedence over file-based configuration.

## Add your own parameters

Let's add a new parameter to control model verbosity. Open `conf/base/parameters_data_science.yml` and add a new parameter:

```yaml
model_options:
  test_size: 0.2
  random_state: 3
  features:
    - engines
    - passenger_capacity
    - crew
    - d_check_complete
    - moon_clearance_complete
    - iata_approved
    - company_rating
    - review_scores_rating
  verbose: true  # New parameter
```

You can now access this parameter in your nodes the same way as the others.

## Add credentials securely

Credentials store sensitive information like API keys and passwords. They should never be committed to version control.

Create or open `conf/local/credentials.yml`:

```yaml
# This file is gitignored by default - never commit it!

dev_s3:
  client_kwargs:
    aws_access_key_id: <your_access_key_id>
    aws_secret_access_key: <your_secret_access_key>

api_credentials:
  key: <your_api_key>
```

!!! warning
    The `conf/local/` folder is automatically excluded from version control. Always store credentials here, never in `conf/base/`.

## Use credentials in your data catalog

Reference credentials in your catalog. Open `conf/base/catalog.yml` and add an example dataset that uses credentials:

```yaml
my_s3_dataset:
  type: pandas.CSVDataset
  filepath: s3://your-bucket/data/my-data.csv
  credentials: dev_s3
```

Kedro automatically resolves the `dev_s3` credentials when loading this dataset.

## Verify your configuration

To verify your configuration is loaded correctly, start an interactive session:

```bash
kedro ipython
```

Then check your parameters:

```python
# Load and view the parameters
params = context.params
print(params["model_options"])
```

You should see:

```python
{
    'test_size': 0.2,
    'random_state': 3,
    'features': ['engines', 'passenger_capacity', 'crew', ...],
    'verbose': True
}
```

Exit the session:

```python
exit()
```

## What you've learned

In this quick start, you:

✅ Explored parameter files in the spaceflights project
✅ Understood how parameters are used in pipeline nodes with the `params:` prefix
✅ Ran pipelines with default and overridden parameters
✅ Added your own parameters to configuration files
✅ Stored credentials securely in the `local` environment
✅ Referenced credentials in your data catalog

## Next steps

Now that you've mastered the basics, explore more advanced features:

- **Understand configuration concepts**: Learn about [configuration basics](./01_configuration_basics.md) and the OmegaConfigLoader
- **Use different environments**: Learn about [base, local, and custom environments](./02_configuration_environments.md) for dev/staging/prod
- **Template your configuration**: Use [variable interpolation](./04_templating_with_omegaconfigloader.md) to avoid duplication with `${...}` syntax
- **Load config in code**: [Access configuration programmatically](./how_to_configure_project.md#load-configuration-in-your-code) for notebooks and scripts
- **Advanced features**: Explore [merge strategies, remote configuration, and custom loaders](./how_to_configure_project.md#load-from-compressed-files)

## Common issues

**Parameters not loading?**

- Check that your file is named `parameters*.yml` or matches the [configuration patterns](./01_configuration_basics.md#configuration-file-patterns-and-naming)
- Verify the file is in `conf/base/` or your active environment
- Check for YAML syntax errors (proper indentation, colons, etc.)

**Credentials exposed in git?**

- Ensure `conf/local/` is in your `.gitignore` (it should be by default)
- Never put credentials in `conf/base/`
- Check that credential files contain "credentials" in their filename

**Runtime parameters not working?**

- Use `--params=` (with equals sign)
- Separate multiple parameters with commas (no spaces): `key1=val1,key2=val2`
- For nested keys, use dot notation: `model_options.test_size=0.3`
- Quote the entire string if values contain spaces: `--params="key=value with spaces"`
