# Configuration

This section contains detailed information about Kedro project configuration, which you can use to store settings for your project such as [parameters](./parameters_explanation.md), [credentials](./credentials_explanation.md), the [data catalog](../catalog-data/data_catalog.md), and [logging information](../develop/logging.md).

Kedro makes use of a configuration loader to load any project configuration files, which you can access through [kedro.config.OmegaConfigLoader][].

!!! note
    `ConfigLoader` and `TemplatedConfigLoader` have been removed in Kedro `0.19.0`. Refer to the [migration guide for config loaders](./config_loader_migration.md) for instructions on how to update your code base to use `OmegaConfigLoader`.

<!-- vale Kedro.headings = NO -->
## OmegaConfigLoader
<!-- vale Kedro.headings = YES -->

[OmegaConf](https://omegaconf.readthedocs.io/) is a Python library designed to handle and manage settings. It serves as a YAML-based hierarchical system to organise configurations, which can be structured to accommodate various sources, allowing you to merge settings from multiple locations.

From Kedro 0.18.5 you can use the [kedro.config.OmegaConfigLoader][] which uses `OmegaConf` to load data.

`OmegaConfigLoader` can load `YAML` and `JSON` files. Acceptable file extensions are `.yml`, `.yaml`, and `.json`. By default, any configuration files used by the config loaders in Kedro are `.yml` files.

### `OmegaConf` vs. Kedro's `OmegaConfigLoader`
`OmegaConf` is a configuration management library in Python that allows you to manage hierarchical configurations. Kedro's `OmegaConfigLoader` uses `OmegaConf` for handling configurations.
This means that when you work with `OmegaConfigLoader` in Kedro, you are using the capabilities of `OmegaConf` without directly interacting with it.

`OmegaConfigLoader` in Kedro is designed to handle more complex configuration setups commonly used in Kedro projects. It automates the process of merging configuration files, such as those for catalogs, and accounts for different environments to make it convenient to manage configurations in a structured way.

When you need to load configurations manually, such as for exploration in a notebook, you have two options:
1. Use the `OmegaConfigLoader` class provided by Kedro.
2. Directly use the `OmegaConf` library.

Kedro's `OmegaConfigLoader` is designed to handle complex project environments. If your use case involves loading a single configuration file and is straightforward, it may be simpler to use `OmegaConf` directly.

```python
from omegaconf import OmegaConf

parameters = OmegaConf.load("/path/to/parameters.yml")
```

When your configuration files are complex and contain credentials or templating, Kedro's `OmegaConfigLoader` is more suitable, as described in more detail in [How to load a data catalog with credentials in code?](how_to_configure_project.md#how-to-load-a-data-catalog-with-credentials-in-code) and [How to load a data catalog with templating in code?](how_to_advanced_configuration.md#how-to-load-a-data-catalog-with-templating-in-code).

In summary, while both `OmegaConf` and Kedro's `OmegaConfigLoader` provide ways to manage configurations, your choice depends on the complexity of your configuration and whether you are working within the context of the Kedro framework.

## Configuration source
The configuration source folder is [`conf`](../getting-started/kedro_concepts.md#conf) by default. We recommend that you keep all configuration files in the default `conf` folder of a Kedro project.

## Configuration environments
A configuration environment is a way of organising your configuration settings for different stages of your data pipeline. For example, you might have different settings for development, testing, and production environments.

By default, Kedro projects have a `base` and a `local` environment.

### Base
In Kedro, the base configuration environment refers to the default configuration settings that are used as the foundation for all other configuration environments.

The `base` folder contains the default settings that are used across your pipelines, unless they are overridden by a specific environment.

!!! warning
    Do not put private access credentials in the base configuration folder or any other configuration environment folder that is stored in version control.

### Local
The `local` configuration environment folder should be used for configuration that is either user-specific (for example, IDE configuration) or protected (for example, security keys).

!!! warning
    Do not add any local configuration to version control.


## Configuration loading
Kedro-specific configuration (for example, [kedro.io.DataCatalog][] configuration for I/O) is loaded using a configuration loader class, by default, this is [kedro.config.OmegaConfigLoader][].
When you interact with Kedro through the command line, for example, by running `kedro run`, Kedro loads all project configuration in the configuration source through this configuration loader.

The loader recursively scans for configuration files inside the `conf` folder, firstly in `conf/base` (`base` being the default environment) and then in `conf/local` (`local` being the designated overriding environment).

Kedro merges configuration information and returns a configuration dictionary according to the following rules:

* If any two configuration files (exception for parameters) located inside the **same** environment path (such as `conf/base/`) contain the same top-level key, the configuration loader raises a `ValueError` indicating that duplicates are not allowed.
* If two configuration files contain the same top-level key but are in **different** environment paths (for example, one in `conf/base/`, another in `conf/local/`) then the last loaded path (`conf/local/`) takes precedence as the key value. `OmegaConfigLoader.__getitem__` does not raise any errors but a `DEBUG` level log message is emitted with information on the overridden keys.
* If any two parameter configuration files contain the same top-level key, the configuration loader checks the sub-keys for duplicates. If there are any, it raises a `ValueError` indicating that duplicates are not allowed.

When using any of the configuration loaders, any top-level keys that start with `_` are considered hidden (or reserved) and are ignored. Those keys will neither trigger a key duplication error nor appear in the resulting configuration dictionary. You can still use such keys, for example, as [YAML anchors and aliases](https://www.educative.io/blog/advanced-yaml-syntax-cheatsheet)
or [to enable templating in the catalog when using the `OmegaConfigLoader`](templating_explanation.md).

### Configuration file names
Configuration files will be matched according to file name and type rules. Suppose the config loader needs to fetch the catalog configuration, it will search according to the following rules:

* *Either* of the following is true:
  * filename starts with `catalog`
  * file is located in a subdirectory whose name is prefixed with `catalog`
* *And* file extension is one of the following: `yaml`, `yml`, or `json`

### Configuration patterns
Under the hood, the Kedro configuration loader loads files based on regex patterns that specify the naming convention for configuration files. These patterns are specified by `config_patterns` in the configuration loader classes.

By default, those patterns are set as follows for the configuration of catalog, parameters, logging, credentials:

```python
config_patterns = {
    "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
    "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
    "logging": ["logging*", "logging*/**", "**/logging*"],
}
```

If you want to change the way configuration is loaded, you can either [customise the config patterns](how_to_advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) or [bypass the configuration loading](how_to_advanced_configuration.md#how-to-bypass-the-configuration-loading-rules) as described in the advanced configuration how-to guide.
