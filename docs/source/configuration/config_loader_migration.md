# Migration guide for config loaders
The `ConfigLoader` and `TemplatedConfigLoader` classes have been deprecated since Kedro `0.18.12` and will be removed in Kedro `0.19.0`. To ensure a smooth transition, we strongly recommend you adopt the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) as soon as possible.
This migration guide outlines the primary distinctions between the old loaders and the `OmegaConfigLoader`, providing step-by-step instructions on updating your code base to utilise the new class effectively.

## [`ConfigLoader`](/kedro.config.ConfigLoader) to [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader)

### 1. Install the Required Library
The [`OmegaConfigLoader`](advanced_configuration.md#omegaconfigloader) was introduced in Kedro `0.18.5` and is based on [OmegaConf](https://omegaconf.readthedocs.io/). In order to use it you need to ensure you have both a version of Kedro of `0.18.5` or above and `omegaconf` installed.
You can install both using `pip`:

```bash
pip install kedro==0.18.5
```
This would be the minimum required Kedro version which includes `omegaconf` as a dependency.
Or you can run:
```bash
pip install -U kedro
```

This command installs the most recent version of Kedro which also includes `omegaconf` as a dependency.

### 2. Use the `OmegaConfigLoader`
To use `OmegaConfigLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md):

```diff
+ from kedro.config import OmegaConfigLoader  # new import

+ CONFIG_LOADER_CLASS = OmegaConfigLoader
```

### 3. Import Statements
Replace the import statement for `ConfigLoader` with the one for `OmegaConfigLoader`:

```diff
- from kedro.config import ConfigLoader

+ from kedro.config import OmegaConfigLoader
```

### 4. File Format Support
`OmegaConfigLoader` supports only `yaml` and `json` file formats. Make sure that all your configuration files are in one of these formats. If you previously used other formats with `ConfigLoader`, convert them to `yaml` or `json`.

### 5. Load Configuration
The method to load the configuration using `OmegaConfigLoader` differs slightly from that used by `ConfigLoader`, which allowed users to access configuration through the `.get()` method and required patterns as argument.
When you migrate to use `OmegaConfigLoader` it  requires you to fetch configuration through a configuration key that points to [configuration patterns specified in the loader class](configuration_basics.md#configuration-patterns) or [provided in the `CONFIG_LOADER_ARGS`](advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) in `settings.py`.

```diff
- conf_path = str(project_path / settings.CONF_SOURCE)
- conf_loader = ConfigLoader(conf_source=conf_path, env="local")
- catalog = conf_loader.get("catalog*")

+ conf_path = str(project_path / settings.CONF_SOURCE)
+ config_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
+ catalog = config_loader["catalog"]
```

In this example, `"catalog"` is the key to the default catalog patterns specified in the `OmegaConfigLoader` class.

### 6. Exception Handling
For error and exception handling, most errors are the same. Those you need to be aware of that are different between the original `ConfigLoader` and `OmegaConfigLoader` are as follows:
* `OmegaConfigLoader` throws a `MissingConfigException` when configuration paths don't exist, rather than the `ValueError` used in `ConfigLoader`.
* In `OmegaConfigLoader`, if there is bad syntax in your configuration files, it will trigger a `ParserError` instead of a `BadConfigException` used in `ConfigLoader`.
