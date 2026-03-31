# Configure Your Project

This page covers:

- [Change the configuration source folder](#change-the-configuration-source-folder)
- [Create and use custom environments](#create-and-use-custom-environments)
- [Set the default environment](#set-the-default-environment)
- [Disable environment overrides](#disable-environment-overrides)
- [Load configuration in your code](#load-configuration-in-your-code)
- [Load from compressed files](#load-from-compressed-files)
- [Load from remote storage](#load-from-remote-storage)
- [Configure file patterns](#configure-file-patterns)
- [Set merge strategy for config overrides](#set-merge-strategy-for-config-overrides)
- [Build a custom configuration loader](#build-a-custom-configuration-loader)
- [Skip configuration loading](#skip-configuration-loading)
- [Include hidden configuration files](#include-hidden-configuration-files)

## Change the configuration source folder

To change the configuration source folder, set `CONF_SOURCE` in `src/<package_name>/settings.py`:

```python
CONF_SOURCE = "config"
```

To change it at runtime:

```bash
kedro run --conf-source=/path/to/config
```

## Create and use custom environments

Create a new environment folder:

```bash
mkdir conf/prod
```

Add environment-specific configuration:

```yaml
# conf/prod/parameters.yml
model_options:
  test_size: 0.1
```

Run with the environment:

```bash
kedro run --env=prod
```

Or set the environment variable:

```bash
export KEDRO_ENV=prod
kedro run
```

## Set the default environment

To change the default from `local` to another environment, set `CONFIG_LOADER_ARGS` in `src/<package_name>/settings.py`:

```python
CONFIG_LOADER_ARGS = {"default_run_env": "prod"}
```

## Disable environment overrides

To use only the `base` environment without any overrides:

```python
CONFIG_LOADER_ARGS = {"default_run_env": "base"}
```

## Load configuration in your code

Load configuration using `OmegaConfigLoader`:

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings
from pathlib import Path

conf_path = str(Path.cwd() / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

parameters = conf_loader["parameters"]
catalog = conf_loader["catalog"]
```

Load with specific environments:

```python
conf_loader = OmegaConfigLoader(
    conf_source="conf",
    base_env="base",
    default_run_env="prod"
)
parameters = conf_loader["parameters"]
```

Use outside a Kedro project:

```python
from kedro.config import OmegaConfigLoader

config_loader = OmegaConfigLoader(conf_source="./my_config")
params = config_loader["parameters"]
```

---

## Load from compressed files

Load configuration from `.tar.gz` or `.zip` files:

```bash
kedro run --conf-source=config.tar.gz
kedro run --conf-source=config.zip
```

Create compressed configuration:

```bash
# Using tar
tar --exclude=local/*.yml -czf config.tar.gz --directory=conf .

# Using zip
zip -x conf/local/** -r config.zip conf
```

## Load from remote storage

Load configuration from cloud storage:

```bash
# Amazon S3
kedro run --conf-source=s3://my-bucket/configs/

# Azure Blob Storage
kedro run --conf-source=abfs://container@account/configs/

# Google Cloud Storage
kedro run --conf-source=gs://my-bucket/configs/
```

Set up authentication via environment variables:

```bash
# Amazon S3
export AWS_ACCESS_KEY_ID=<your_access_key>
export AWS_SECRET_ACCESS_KEY=<your_secret_key>

# Google Cloud
gcloud auth application-default login

# Azure
export AZURE_STORAGE_ACCOUNT=<your_account>
export AZURE_STORAGE_KEY=<your_key>
```

## Configure file patterns

Change which files are loaded for each configuration type:

```python
# src/my_project/settings.py
CONFIG_LOADER_ARGS = {
    "config_patterns": {
        "parameters": ["params*", "params*/**", "**/params*"],
        "spark": ["spark*", "spark*/**", "**/spark*"],
    }
}
```

## Set merge strategy for config overrides

By default, configuration uses **destructive merge**. Change to **soft merge** to preserve all keys:

```python
# src/my_project/settings.py
CONFIG_LOADER_ARGS = {
    "merge_strategy": {
        "parameters": "soft",
        "catalog": "destructive",
    }
}
```

**Destructive merge** (default): `{a: 1, b: 2}` + `{a: 3}` = `{a: 3}`

**Soft merge**: `{a: 1, b: 2}` + `{a: 3}` = `{a: 3, b: 2}`

## Build a custom configuration loader

Extend `AbstractConfigLoader` for custom behavior:

```python
from kedro.config import AbstractConfigLoader

class CustomConfigLoader(AbstractConfigLoader):
    def __init__(self, conf_source, env=None, runtime_params=None):
        super().__init__(
            conf_source=conf_source,
            env=env,
            runtime_params=runtime_params
        )
        # Custom implementation

# src/my_project/settings.py
CONFIG_LOADER_CLASS = CustomConfigLoader
```

## Skip configuration loading

Set configuration directly on the loader:

```python
from kedro.config import OmegaConfigLoader

conf_loader = OmegaConfigLoader(conf_source="conf")
conf_loader["catalog"] = {"my_dataset": {"type": "pandas.CSVDataset"}}
```

## Include hidden configuration files

By default, hidden files (starting with `.`) are ignored:

```python
conf_loader = OmegaConfigLoader(conf_source="conf", ignore_hidden=False)
```
