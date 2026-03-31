# Configuration Environments

Configuration environments in Kedro allow you to organize your settings for different stages of your data pipeline. With environments, you can maintain separate configurations for development, testing, staging, and production without duplicating code.

## Understanding environments

A configuration environment is a folder within your `conf/` directory that contains configuration files. Kedro loads configuration by combining files from multiple environments in a specific order, allowing you to define base settings and override them for specific contexts.

### Base environment

The `base` environment contains your default configuration settings that apply across all stages of your project. These are the foundational settings that remain consistent regardless of where or how you run your pipeline.

```
conf/base/
├── catalog.yml          # Dataset definitions
├── parameters.yml       # Default parameter values
└── logging.yml          # Logging configuration
```

The `base` folder typically includes:
- Dataset catalog entries that work across environments
- Default parameter values for your pipeline
- Common logging configuration
- Shared settings used by all team members

!!! warning
    Never store credentials, API keys, or other sensitive information in the `base` environment. These files are typically committed to version control and shared across your team.

### Local environment

The `local` environment is designed for user-specific or sensitive configuration that should never be committed to version control.

```
conf/local/
├── credentials.yml      # API keys, passwords, tokens
└── parameters.yml       # Personal parameter overrides
```

By default, Kedro's `.gitignore` is configured to exclude the `local/` folder from version control. Use this environment for:
- Credentials and secrets (database passwords, API keys, access tokens)
- Personal development settings (local file paths, debug flags)
- Temporary overrides for testing

!!! warning
    Never commit the `local/` environment to version control. Keep sensitive information secure by storing it only in this folder.

### Custom environments

Beyond `base` and `local`, you can create any number of custom environments for your specific needs:

```
conf/
├── base/
├── local/
├── dev/                 # Development environment
├── staging/             # Staging environment
└── prod/                # Production environment
```

Custom environments are useful for:
- Different deployment targets (AWS vs Azure)
- Separate data sources (test database vs production database)
- Varied resource allocations (small clusters vs large clusters)
- Environment-specific feature flags

## How configuration loading and merging works

When Kedro loads configuration, it follows a systematic process to combine files from multiple environments.

### Loading order

1. **Base environment loads first**: Kedro starts by loading all matching files from `conf/base/`
2. **Override environment loads second**: Kedro then loads files from the override environment (by default, `conf/local/`)
3. **Merging occurs**: Configuration from the override environment is merged with the base configuration

For example, if you run `kedro run` without specifying an environment:

```bash
kedro run  # Loads base, then local
```

Kedro loads `conf/base/` first, then merges in `conf/local/`.

If you specify a custom environment:

```bash
kedro run --env=prod  # Loads base, then prod
```

Kedro loads `conf/base/` first, then merges in `conf/prod/`.

### Merge behavior and precedence rules

The way configuration merges depends on where the files are located and what merge strategy is configured.

#### Files in the same environment

When multiple files in the **same environment** contain the same top-level key, Kedro raises a `ValueError`:

```
conf/base/
├── catalog.yml          # Contains: datasets:
└── catalog_extra.yml    # Contains: datasets:  ❌ ERROR!
```

This prevents accidental duplication. If you want to split your configuration across multiple files, use different top-level keys or organize them in subdirectories.

#### Files in different environments

When files in **different environments** contain the same top-level key, the override environment takes precedence:

```yaml
# conf/base/parameters.yml
model_options:
  learning_rate: 0.01
  epochs: 100

# conf/local/parameters.yml
model_options:
  learning_rate: 0.05  # This overrides the base value
```

By default, Kedro uses **destructive merging** for configuration in different environments:
- The entire `model_options` dictionary from `local` replaces the one from `base`
- Only the `learning_rate: 0.05` remains; `epochs: 100` is discarded

You can change this behavior to use **soft merging** where all keys are preserved. See [how to change merge strategies](./how_to_configure_project.md#change-merge-strategies) for details.

#### Parameters special handling

Parameters receive special treatment during merging. For parameter files, Kedro checks **sub-keys** for duplicates:

```yaml
# conf/base/parameters.yml
model_options:
  learning_rate: 0.01

# conf/local/parameters.yml
model_options:
  learning_rate: 0.05  # ❌ ERROR! Duplicate sub-key
```

This raises a `ValueError` because `learning_rate` appears in both files. To override parameter values, you should use the [runtime parameters](./how_to_work_with_parameters.md#override-parameters-at-runtime) feature or adjust your merge strategy.

### Precedence summary

Configuration precedence from lowest to highest:

1. **Base environment** (`conf/base/`)
2. **Override environment** (`conf/local/`, `conf/prod/`, etc.)
3. **Runtime parameters** (passed via `--params` flag)

Later sources override earlier ones according to the merge strategy in effect.

### Debug logging

When configuration is overridden, Kedro emits a `DEBUG` level log message indicating which keys were replaced. If you're troubleshooting unexpected configuration values, enable debug logging to see the merge details:

```bash
kedro run --log-level=DEBUG
```

## Conflict resolution

Understanding how Kedro handles configuration conflicts helps you structure your files effectively:

| Scenario | Result |
|----------|--------|
| Same top-level key in same environment | `ValueError` raised |
| Same top-level key in different environments | Override environment wins (merge strategy applies) |
| Same sub-key in parameter files | `ValueError` raised (by default) |
| Hidden keys (starting with `_`) | Never cause conflicts |

## Where to go next

Now that you understand configuration environments, you can:

- [Create and use custom environments](./how_to_configure_project.md#create-and-use-custom-environments) for dev/staging/prod
- [Change the default overriding environment](./how_to_configure_project.md#change-the-default-overriding-environment) from `local` to something else
- [Change merge strategies](./how_to_configure_project.md#change-merge-strategies) for soft vs destructive merging
- Learn about [parameters and credentials](./03_parameters_and_credentials.md)
