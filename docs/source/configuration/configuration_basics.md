# Configuration basics

This section contains detailed information about Kedro project configuration. Project configuration is the configuration inside the [`/conf`](../get_started/kedro_concepts.md#conf) directory of your Kedro project.
By default, the files stored in this directory allow you to configure [parameters](configuration.md#parameters), [credentials](configuration.md#credentials), the [data catalog](../data/data_catalog.md), and [logging](../logging/logging.md).

Kedro makes use of a configuration loader to load any project configuration files. The available configuration loader classes are: [`ConfigLoader`](/kedro.config.ConfigLoader), [`TemplatedConfigLoader`](/kedro.config.TemplatedConfigLoader), and [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader).
By default, Kedro uses the `ConfigLoader`, for which the relevant API documentation can be found in [kedro.config.ConfigLoader](/kedro.config.ConfigLoader). In the following sections and examples, you can assume the default `ConfigLoader` is used, unless otherwise specified.

## Configuration source
The configuration source is the source folder where the Kedro project configuration is stored. We recommend that you keep all configuration files in the default `conf` directory of a Kedro project.

## Configuration environments
A configuration environment is a way of organising your configuration settings for different stages of your data pipeline. For example, you might have different settings for development, testing, and production environments.
By default, Kedro has a `local` and `base` environment.

### Local
The `local` configuration environment folder should be used for configuration that is either user-specific (e.g. IDE configuration) or protected (e.g. security keys).

```{note}
Please do not check in any local configuration to version control.
```

### Base
In Kedro, the base configuration environment refers to the default configuration settings that are used as the foundation for all other configuration environments in your pipeline.
This directory contains the default settings that are used across all environments in your pipeline, unless they are overridden by a specific environment.

```{note}
Do not put access credentials in the base configuration folder or any other configuration environment directory that is set up with version control.
```

Configuration information from files stored in `base` or `local` that match these rules is merged at runtime and returned as a config dictionary:
* If any two configuration files located inside the same environment path (`conf/base/` or `conf/local/` in the default setup) contain the same top-level key, the configuration loader will raise a `ValueError` indicating that duplicates are not allowed.
* If two configuration files have duplicate top-level keys but are in different environment paths (one in `conf/base/`, another in `conf/local/`, for example) then the last loaded path (`conf/local/` in this case) takes precedence and overrides that key value. `ConfigLoader.get` will not raise any errors - however, a `DEBUG` level log message will be emitted with information on the overridden keys.

When using the default `ConfigLoader` or the `TemplatedConfigLoader`, any top-level keys that start with `_` are considered hidden (or reserved) and are ignored after the config is loaded. Those keys will neither trigger a key duplication error nor appear in the resulting configuration dictionary. However, you can still use such keys, for example, as [YAML anchors and aliases](https://www.educative.io/blog/advanced-yaml-syntax-cheatsheet#anchors).

## Configuration loading
Kedro-specific configuration (e.g., `DataCatalog` configuration for IO) is loaded using a configuration loader class, by default, the `ConfigLoader` class.
When you interact with Kedro through the command line, e.g. by running `kedro run`, Kedro will load all project configuration in the configuration source through this configuration loader.

The loader recursively scans for configuration files inside the `conf` directory, firstly in the `conf/base/` (`base` being the default environment) and then in the `conf/local/` (`local` being the designated overriding environment) directory.
Files will be matched according to file name and type rules. Suppose the config loader needs to fetch the catalog configuration, it will search according to the following rules:

* *Either* of the following is true:
  * filename starts with `catalog`
  * file is located in a sub-directory whose name is prefixed with `catalog`
* *And* file extension is one of the following: `yaml`, `yml`, `json`, `ini`, `pickle`, `xml` or `properties` for the `ConfigLoader` and `TemplatedConfigLoader` or `yaml`, `yml`, or `json` for the `OmegaConfigLoader`.


## Basic configuration how-tos

### How to change the configuration source folder?
If you prefer to store the Kedro project configuration in a different directory than the `conf` directory inside your project you can change the configuration source by setting the `CONF_SOURCE` variable in [`src/<package_name>/settings.py`](settings.md) as follows:

```python
CONF_SOURCE = "new_conf"
```

### How to change the configuration source folder at run time?
You can specify a source directory for the configuration files at run time using the [`kedro run` CLI command](../development/commands_reference.md#modifying-a-kedro-run) with the `--conf-source` flag as follows:

```bash
kedro run --conf-source=<path-to-new-conf-directory>
```

### How to read configuration from a compressed file? (POTENTIALLY ADVANCED QUESTION)
You can read configuration from a compressed file in `tar.gz` or `zip` format by using the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader).
The two commands below are examples of how to reference a `tar.gz` or `zip` file:

 ```bash
kedro run --conf-source=<path-to-compressed-file>.tar.gz

kedro run --conf-source=<path-to-compressed-file>.zip
```

To compress your configuration you can either leverage Kedro's `kedro package` command which builds the package into the `dist/` folder of your project, and creates one `.egg` file, one `.whl` file, as well as a `tar.gz` file containing the project configuration. This compressed version of the config files excludes any files inside your `local` directory.
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
├── base               <-- the files inside be different, but this is an example of a standard Kedro structure.
│   └── parameters.yml
│   └── catalog.yml
└── local              <-- the top level local directory is required, but no files should be inside when distributed.
└── README.md          <-- optional but included with the default Kedro conf structure.
```

### How to directly access configuration for e.g. debugging?
If you want to directly access configuration in code, for example to debug, you can do so as follows:

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

# Instantiate a ConfigLoader with the location of your project configuration.
conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path)

# This line shows how to access the catalog configuration. You can access other configuration in the same way.
conf_catalog = conf_loader["catalog"]
```

### How to use additional configuration environments to base and local?
In addition to the two built-in local and base configuration environments, you can create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create, such as `conf/server/` or `conf/test/`. To use additional configuration environments, run the following command:

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

### How to change the default overriding environment?
By default, `local` is the overriding environment for `base`. If you want to change this, you must customise the configuration loader argument settings you're using to set `default_run_env` in `src/<package_name>/settings.py` under the `CONFIG_LOADER_ARGS` key.
For example, if you want to always override `base` configuration with configuration in a custom environment called `prod`, you change the configuration loader arguments like this:

```python
CONFIG_LOADER_ARGS = {"default_run_env": "prod"}
```

### How to use only one configuration environment?
If, for some reason, your project does not have any other environments apart from `base`, i.e. no `local` environment to default to, you must customise the configuration loader argument settings you're using to set `"default_run_env": "base"` in `src/<package_name>/settings.py` under the `CONFIG_LOADER_ARGS` key.

```python
CONFIG_LOADER_ARGS = {"default_run_env": "base"}
```
