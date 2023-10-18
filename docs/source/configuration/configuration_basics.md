# Configuration

This section contains detailed information about Kedro project configuration, which you can use to store settings for your project such as [parameters](./parameters.md), [credentials](./credentials.md), the [data catalog](../data/data_catalog.md), and [logging information](../logging/index.md).

Kedro makes use of a configuration loader to load any project configuration files, and the available configuration loader classes are:

```{warning}
`ConfigLoader` and `TemplatedConfigLoader` have been deprecated since Kedro `0.18.12` and will be removed in Kedro `0.19.0`. Refer to the [migration guide for config loaders](./config_loader_migration.md) for instructions on how to update your code base to use `OmegaConfigLoader`.
```

* [`ConfigLoader`](/kedro.config.ConfigLoader)
* [`TemplatedConfigLoader`](/kedro.config.TemplatedConfigLoader)
* [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader).

By default, Kedro uses the `ConfigLoader`. However, in projects created with Kedro `0.18.13` onwards, `OmegaConfigLoader` has been set as the config loader as the default in the project's `src/<package_name>/settings.py` file.
You can select which config loader you want to use in your project by modifying the `src/<package_name>/settings.py` like this:
```python
from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader
```
The following sections and examples are valid for both, the `ConfigLoader` and the `OmegaConfigLoader`. The [advanced configuration documentation](./advanced_configuration.md) covers use of the [`TemplatedConfigLoader`](/kedro.config.TemplatedConfigLoader)
and the advanced use cases of the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader) in more detail.


## Configuration source
The configuration source folder is [`conf`](../get_started/kedro_concepts.md#conf) by default. We recommend that you keep all configuration files in the default `conf` folder of a Kedro project.

## Configuration environments
A configuration environment is a way of organising your configuration settings for different stages of your data pipeline. For example, you might have different settings for development, testing, and production environments.

By default, Kedro has a `base` and a `local` environment.

### Base
In Kedro, the base configuration environment refers to the default configuration settings that are used as the foundation for all other configuration environments.

The `base` folder contains the default settings that are used across your pipelines, unless they are overridden by a specific environment.

```{warning}
Do not put private access credentials in the base configuration folder or any other configuration environment folder that is stored in version control.
```

### Local
The `local` configuration environment folder should be used for configuration that is either user-specific (e.g. IDE configuration) or protected (e.g. security keys).

```{warning}
Do not add any local configuration to version control.
```

## Configuration loading
Kedro-specific configuration (e.g., `DataCatalog` configuration for I/O) is loaded using a configuration loader class, by default, this is [`ConfigLoader`](/kedro.config.ConfigLoader) for
projects created with Kedro `0.18.13` or older and has been set to `OmegaConfigLoader` for projects created with Kedro `0.18.13` onwards.
When you interact with Kedro through the command line, e.g. by running `kedro run`, Kedro loads all project configuration in the configuration source through this configuration loader.

The loader recursively scans for configuration files inside the `conf` folder, firstly in `conf/base` (`base` being the default environment) and then in `conf/local` (`local` being the designated overriding environment).

Kedro merges configuration information and returns a configuration dictionary according to the following rules:

* If any two configuration files located inside the **same** environment path (such as `conf/base/`) contain the same top-level key, the configuration loader raises a `ValueError` indicating that duplicates are not allowed.
* If two configuration files contain the same top-level key but are in **different** environment paths (for example, one in `conf/base/`, another in `conf/local/`) then the last loaded path (`conf/local/`) takes precedence as the key value. `ConfigLoader.get` does not raise any errors but a `DEBUG` level log message is emitted with information on the overridden keys.

When using any of the configuration loaders, any top-level keys that start with `_` are considered hidden (or reserved) and are ignored. Those keys will neither trigger a key duplication error nor appear in the resulting configuration dictionary. However, you can still use such keys, for example, as [YAML anchors and aliases](https://www.educative.io/blog/advanced-yaml-syntax-cheatsheet)
or [to enable templating in the catalog when using the `OmegaConfigLoader`](advanced_configuration.md#how-to-do-templating-with-the-omegaconfigloader).

### Configuration file names
Configuration files will be matched according to file name and type rules. Suppose the config loader needs to fetch the catalog configuration, it will search according to the following rules:

* *Either* of the following is true:
  * filename starts with `catalog`
  * file is located in a subfolder whose name is prefixed with `catalog`
* *And* file extension is one of the following:
    * `yaml`, `yml`, `json`, `ini`, `pickle`, `xml` or `properties` for the `ConfigLoader` and `TemplatedConfigLoader`
    * `yaml`, `yml`, or `json` for the `OmegaConfigLoader`

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

If you want to change the way configuration is loaded, you can either [customise the config patterns](advanced_configuration.md#how-to-change-which-configuration-files-are-loaded) or [bypass the configuration loading](advanced_configuration.md#how-to-bypass-the-configuration-loading-rules) as described in the advanced configuration chapter.

## How to use Kedro configuration

This section contains a set of guidance for the most common configuration requirements of standard Kedro projects:

* [How to change the setting for a configuration source folder](#how-to-change-the-setting-for-a-configuration-source-folder)
* [How to change the configuration source folder at runtime](#how-to-change-the-configuration-source-folder-at-runtime)
* [How to read configuration from a compressed file](#how-to-read-configuration-from-a-compressed-file)
* [How to access configuration in code](#how-to-access-configuration-in-code)
* [How to specify additional configuration environments](#how-to-specify-additional-configuration-environments)
* [How to change the default overriding environment](#how-to-change-the-default-overriding-environment)
* [How to use only one configuration environment](#how-to-use-only-one-configuration-environment)

### How to change the setting for a configuration source folder
To store the Kedro project configuration in a different folder to `conf`, change the configuration source by setting the `CONF_SOURCE` variable in [`src/<package_name>/settings.py`](../kedro_project_setup/settings.md) as follows:

```python
CONF_SOURCE = "new_conf"
```

### How to change the configuration source folder at runtime
Specify a source folder for the configuration files at runtime using the [`kedro run` CLI command](../development/commands_reference.md#modifying-a-kedro-run) with the `--conf-source` flag as follows:

```bash
kedro run --conf-source=<path-to-new-conf-folder>
```

### How to read configuration from a compressed file
You can read configuration from a compressed file in `tar.gz` or `zip` format by using the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader).

How to reference a `tar.gz` file:

 ```bash
kedro run --conf-source=<path-to-compressed-file>.tar.gz
```

How to reference a `zip` file:

```bash
kedro run --conf-source=<path-to-compressed-file>.zip
```

To compress your configuration you can use Kedro's `kedro package` command which builds the package into the `dist/` folder of your project, and creates a `.whl` file, as well as a `tar.gz` file containing the project configuration. The compressed version of the config files excludes any files inside your `local` folder.

Alternatively you can run the command below to create a `tar.gz` file:

```bash
tar --exclude=local/*.yml -czf <my_conf_name>.tar.gz --directory=<path-to-conf-dir> <conf-dir>
```

Or the following command to create a `zip` file:

```bash
zip -x <conf-dir>/local/** -r <my_conf_name>.zip <conf-dir>
```

Note that for both the `tar.gz` and `zip` file the following structure is expected:

```text
<conf_dir>
├── base               <-- the files inside may be different, but this is an example of a standard Kedro structure.
│   └── parameters.yml
│   └── catalog.yml
└── local              <-- the top level local folder is required, but no files should be inside when distributed.
└── README.md          <-- optional but included with the default Kedro conf structure.
```

### How to access configuration in code
To directly access configuration in code, for example to debug, you can do so as follows:

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

# Instantiate a ConfigLoader with the location of your project configuration.
conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

# This line shows how to access the catalog configuration. You can access other configuration in the same way.
conf_catalog = conf_loader["catalog"]
```

### How to specify additional configuration environments
In addition to the two built-in `local` and `base` configuration environments, you can create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create, such as `conf/server/` or `conf/test/`. To use additional configuration environments, run the following command:

```bash
kedro run --env=<your-environment>
```

If no `env` option is specified, this will default to using the `local` environment to overwrite `conf/base`.

If you set the `KEDRO_ENV` environment variable to the name of your environment, Kedro will load that environment for your `kedro run`, `kedro ipython`, `kedro jupyter notebook` and `kedro jupyter lab` sessions:

```bash
export KEDRO_ENV=<your-environment>
```

```{note}
If you both specify the `KEDRO_ENV` environment variable and provide the `--env` argument to a CLI command, the CLI argument takes precedence.
```

### How to change the default overriding environment
By default, `local` is the overriding environment for `base`. To change the folder, customise the configuration loader argument settings in `src/<package_name>/settings.py` and set the `CONFIG_LOADER_ARGS` key to have a new `default_run_env` value.

For example, if you want to override `base` with configuration in a custom environment called `prod`, you change the configuration loader arguments in `settings.py` as follows:

```python
CONFIG_LOADER_ARGS = {"default_run_env": "prod"}
```

### How to use only one configuration environment
If, for some reason, your project does not have any other environments apart from `base`, i.e. no `local` environment to default to, you must customise the configuration loader argument settings in `src/<package_name>/settings.py` and set the `CONFIG_LOADER_ARGS` key to `"default_run_env": "base"`

```python
CONFIG_LOADER_ARGS = {"default_run_env": "base"}
```
