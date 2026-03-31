# Configuration Basics

Kedro uses a configuration system to manage settings for your data pipeline projects. Configuration allows you to separate your code from environment-specific settings like file paths, database credentials, model parameters, and other values that might change between development, testing, and production environments.

## What is configuration in Kedro

Configuration in Kedro refers to any settings stored outside your Python code in structured files. This includes:

- **Parameters**: Values that control your pipeline behavior, such as model hyperparameters, test/train split ratios, or feature engineering settings
- **Credentials**: Sensitive information like API keys, database passwords, or cloud storage access tokens
- **Data catalog**: Definitions of your datasets, including their types, file paths, and loading/saving options
- **Logging**: Settings that control how Kedro logs information during pipeline execution

By storing these settings in configuration files rather than hardcoding them, you can:

- Run the same code in different environments without modification
- Change settings without editing code
- Keep sensitive credentials out of version control
- Override values at runtime for experimentation

## Configuration source and file structure

By default, Kedro stores all configuration files in the `conf/` folder at the root of your project:

```
my_project/
├── conf/
│   ├── base/
│   │   ├── catalog.yml
│   │   ├── parameters.yml
│   │   └── logging.yml
│   └── local/
│       ├── credentials.yml
│       └── parameters.yml
├── data/
├── src/
└── ...
```

The `conf/` folder is called the **configuration source**. Within this folder, Kedro organizes configuration into **environments** (like `base/` and `local/`) that allow you to layer settings appropriately. You can read more about how environments work in [Configuration Environments](./02_configuration_environments.md).

## OmegaConfigLoader overview

Kedro uses `OmegaConfigLoader` as its default configuration loader. This component is responsible for finding, loading, and merging your configuration files.

`OmegaConfigLoader` is built on top of [OmegaConf](https://omegaconf.readthedocs.io/), a Python library designed to handle hierarchical configuration. It provides several key capabilities:

- **Automatic file discovery**: Finds configuration files based on naming patterns
- **Multi-environment support**: Merges configuration from different environment folders
- **Variable interpolation**: Allows you to reference values from other parts of your configuration using `${...}` syntax
- **Type preservation**: Maintains proper data types (strings, numbers, booleans, lists, dictionaries) when loading YAML/JSON
- **Flexible overriding**: Supports runtime parameter overrides via command-line flags

`OmegaConfigLoader` supports **YAML** and **JSON** file formats with the following extensions:
- `.yml`
- `.yaml`
- `.json`

By default, Kedro projects use `.yml` files for configuration.

### When to use OmegaConfigLoader vs OmegaConf directly

Since `OmegaConfigLoader` is built on OmegaConf, you can use either tool to load configuration. Here's when to use each:

**Use OmegaConf directly when:**
- You need to load a single configuration file in a notebook or script
- Your use case is straightforward and doesn't involve multiple environments
- You're working outside a Kedro project context

```python
from omegaconf import OmegaConf

parameters = OmegaConf.load("/path/to/parameters.yml")
```

**Use OmegaConfigLoader when:**
- You're working within a Kedro project
- You need to manage multiple environments (base, local, production, etc.)
- Your configuration includes credentials that need special handling
- You want to use templating or variable interpolation across files
- You need to merge configuration from multiple sources

`OmegaConfigLoader` is designed specifically for Kedro's project structure and handles the complexity of multi-environment configuration management automatically. If you're building a standard Kedro pipeline, you'll typically use `OmegaConfigLoader`.

## Configuration file patterns and naming

`OmegaConfigLoader` finds configuration files by matching their names against predefined patterns. By default, it recognizes the following configuration types:

| Configuration Type | Matching Patterns |
|-------------------|-------------------|
| **catalog** | `catalog*`, `catalog*/**`, `**/catalog*` |
| **parameters** | `parameters*`, `parameters*/**`, `**/parameters*` |
| **credentials** | `credentials*`, `credentials*/**`, `**/credentials*` |
| **logging** | `logging*`, `logging*/**`, `**/logging*` |

This means a file will be recognized as catalog configuration if:
- Its filename starts with `catalog` (e.g., `catalog.yml`, `catalog_spark.yml`), OR
- It's located in a subdirectory whose name starts with `catalog` (e.g., `conf/base/catalog/pipelines.yml`)

These patterns give you flexibility in organizing your configuration. For example, instead of one large `parameters.yml` file, you could create:

```
conf/base/
├── parameters.yml
├── parameters_training.yml
└── parameters/
    ├── data_processing.yml
    └── model_config.yml
```

All of these files would be loaded and merged together as "parameters" configuration.

### Reserved and hidden files

Any configuration file or top-level key that starts with an underscore `_` is considered **hidden** or **reserved**:

- These files are ignored during configuration loading
- Keys starting with `_` don't appear in the resulting configuration dictionary
- They don't trigger duplicate key errors
- They're useful for YAML anchors/aliases and templating values

For example:

```yaml
# catalog.yml
_dataset_defaults:  # This key is hidden
  type: pandas.CSVDataset

my_dataset:
  <<: *dataset_defaults  # Can still reference it with YAML anchors
  filepath: data/my_data.csv
```

The `_dataset_defaults` key won't appear in your loaded catalog configuration, but you can still use it within the file.

## Where to go next

Now that you understand Kedro's configuration basics, you can:

- Learn how [configuration environments](./02_configuration_environments.md) enable multi-stage deployments
- Follow the [Quick Start guide](./quick_start.md) to set up your first configuration
- Discover how to [change the configuration source folder](./how_to_configure_project.md#change-the-configuration-source-folder)
- Explore [configuration file patterns customization](./how_to_configure_project.md#customize-configuration-file-patterns)
