## Migration guide for config loaders
The `ConfigLoader` and `TemplatedConfigLoader` classes are now deprecated and scheduled for removal in Kedro `0.19.0`. To ensure smooth transitions for users, we strongly recommend adopting the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) promptly.
This migration guide outlines the primary distinctions between the old loaders and the `OmegaConfigLoader`, providing step-by-step instructions on updating your code base to utilise the new class effectively.

### [`ConfigLoader`](/kedro.config.ConfigLoader) to [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader)

### 1. Install the Required Library
The [`OmegaConfigLoader`](advanced_configuration.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). In order to use it you need to ensure you have both a version of Kedro of `0.18.5` or above and `omegaconf` installed.
You can install both using `pip`:

```bash
pip install kedro==0.18.5
```
This would be the minimum required Kedro version which includes `omegaconf` as dependency.
Or you can run:
```bash
pip install -U kedro
```

This command installs the most recent version of Kedro which also includes `omegaconf` as dependency.

### 2. Import Statements
Replace the import statement for `ConfigLoader` with the one for `OmegaConfigLoader`:

```python
# Before:
from kedro.config import ConfigLoader

# After:
from kedro.config import OmegaConfigLoader
```

### 3. File Format Support
`OmegaConfigLoader` supports only `yaml` and `json` file formats. Make sure that all your configuration files are in one of these formats. If you were using other formats with `ConfigLoader`, convert them to `yaml` or `json`.

### 4. Load Configuration
The method to load the configuration using `OmegaConfigLoader` is slightly updated. The `ConfigLoader` allowed users to access configuration through the `.get()` method, which required patterns as argument.
The `OmegaConfigLoader` requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

```python
# Before:
conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")
catalog = conf_loader.get("catalog*")

# After:
conf_path = str(project_path / settings.CONF_SOURCE)
config_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
catalog = config_loader["catalog"]
```

In this example, `"catalog"` is the key to the default catalog patterns specified in the `OmegaConfigLoader` class.

### 5. Exception Handling
* `OmegaConfigLoader` throws a `MissingConfigException` when configuration paths don't exist, rather than the `ValueError` used in `ConfigLoader`.
* In `OmegaConfigLoader`, if there is bad syntax in your configuration files, it will trigger a `ParserError` instead of a `BadConfigException` used in `ConfigLoader`.
