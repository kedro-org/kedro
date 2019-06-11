# Configuration

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

This section contains detailed information about configuration. You may also want to consult the relevant API documentation on [kedro.config](/kedro.config.rst).

## Local and base configuration

We recommend that you keep all configuration files in the `conf` directory of a Kedro project. However, if you prefer, you may point Kedro to any other directory and change the configuration paths by modifying the `CONF_ROOT` variable in `src/run.py`.

## Loading

Kedro-specific configuration (e.g., `DataCatalog` configuration for IO) is loaded using the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader

conf_paths = ['conf/base', 'conf/local']
conf_loader = ConfigLoader(conf_paths)
conf_catalog = conf_loader.get('catalog*', 'catalog*/**')
```

This will recursively scan for configuration files firstly in `conf/base/` and then in `conf/local/` directory according to the following rules:

* ANY of the following is true:
  * filename starts with `catalog` OR
  * file is located in a sub-directory whose name is prefixed with `catalog`
* AND file extension is one of the following: `yaml`, `yml`, `json`, `ini`, `pickle`, `xml`, `properties` or `shellvars`

Configuration information from files stored in `base` or `local` that match these rules is merged at runtime and returned in the form of a config dictionary:

* If any 2 configuration files located inside the same environment path (`conf/base/` or `conf/local/` in this example) contain the same top-level key, `load_config` will raise a `ValueError` indicating that the duplicates are not allowed.

> *Note:* Any top-level keys that start with `_` character are considered hidden (or reserved) and therefore are ignored right after the config load. Those keys will neither trigger a key duplication error mentioned above, nor will they appear in the resulting configuration dictionary. However, you may still use such keys for various purposes. For example, as [YAML anchors and aliases](https://confluence.atlassian.com/bitbucket/yaml-anchors-960154027.html).

* If 2 configuration files have duplicate top-level keys, but are placed into different environment paths (one in `conf/base/`, another in `conf/local/`, for example) then the last loaded path (`conf/local/` in this case) takes precedence and overrides that key value. `ConfigLoader.get(<pattern>, ...)` will not raise any errors, however a `DEBUG` level log message will be emitted with the information on the over-ridden keys.


## Additional configuration environments

In addition to the 2 built-in configuration environments, it is possible to create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create. You are be able to create environments like `conf/server/`, `conf/test/`, etc. Any additional configuration environments can be created inside `conf` folder and loaded by running the following command:

```bash
kedro run --env=test
```

If no `env` option is specified, this will default to using `local` environment to overwrite `conf/base`. 

You can alternatively change the default environment by modifying the `DEFAULT_RUN_ENV` variable in `src/run.py`.

```python
DEFAULT_RUN_ENV = "test"
```
