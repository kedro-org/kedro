# Configuration

> *Note:* This documentation is based on `Kedro 0.15.4`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.
>
> This section contains detailed information about configuration.

Relevant API documentation: [ConfigLoader](/kedro.config.ConfigLoader)

## Local and base configuration

We recommend that you keep all configuration files in the `conf` directory of a Kedro project. However, if you prefer, you may point Kedro to any other directory and change the configuration paths by overriding `CONF_ROOT` variable from the derived `ProjectContext` class in `src/<project-package>/run.py` as follows:
```python
class ProjectContext(KedroContext):
    CONF_ROOT = "new_conf"
    # ...
```

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
* If the same environment path is passed multiple times, a `UserWarning` will be emitted to draw attention to the duplicate loading attempt, and any subsequent loading after the first one will be skipped.


## Additional configuration environments

In addition to the 2 built-in configuration environments, it is possible to create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create. You are be able to create environments like `conf/server/`, `conf/test/`, etc. Any additional configuration environments can be created inside `conf` folder and loaded by running the following command:

```bash
kedro run --env=test
```

If no `env` option is specified, this will default to using `local` environment to overwrite `conf/base`.

You can alternatively pass a different environment value in the constructor of `ProjectContext` in `src/run.py`.

```python
env = "test"
```

> *Note*: If, for some reason, your project does not have any other environments apart from `base`, i.e. no `local` environment to default to, the recommended course of action is to use the approach above, namely customise your `ProjectContext` to take `env="base"` in the constructor.


## Credentials

> *Note:* For security reasons, we strongly recommend *not* committing any credentials or other secrets to the Version Control System. Hence, by default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not committed to your git repository.

Credentials configuration can be loaded the same way as any other project configuration using the `ConfigLoader` class:

```python
from kedro.config import ConfigLoader

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)
credentials = conf_loader.get("credentials*", "credentials*/**")
```

This will load all configuration files from `conf/base` and `conf/local`, which either have the filename starting with `credentials` or are located inside a folder with name starting with `credentials`.

> *Note:* Configuration path `conf/local` takes precedence in the example above since it's loaded last, therefore any overlapping top-level keys from `conf/base` will be overwritten by the ones from `conf/local`.

Calling `conf_loader.get()` in the example above will throw a `MissingConfigException` error if there are no configuration files matching the given patterns in any of the specified paths. If this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import ConfigLoader, MissingConfigException

conf_paths = ["conf/base", "conf/local"]
conf_loader = ConfigLoader(conf_paths)

try:
    credentials = conf_loader.get("credentials*", "credentials*/**")
except MissingConfigException:
    credentials = {}
```

> *Note:* `kedro.context.KedroContext` class uses the approach above to load project credentials.

Credentials configuration can then be used on its own or fed into the `DataCatalog` as described in [this section](./04_data_catalog.md#feeding-in-credentials).

### AWS credentials

When working with AWS S3-backed datasets (e.g., `kedro.io.CSVS3DataSet`), you are not required to store AWS credentials in the project configuration files. Instead, you can specify them using environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, optionally, `AWS_SESSION_TOKEN`. Please refer to the [official documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.
