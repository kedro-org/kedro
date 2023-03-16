## Credentials

For security reasons, we strongly recommend you to *not* commit any credentials or other secrets to the Version Control System. Hence, by default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not committed to your git repository.

### Load credentials
Credentials configuration can be loaded the same way as any other project configuration using any of the configuration loader classes: `ConfigLoader`, `TemplatedConfigLoader`, and `OmegaConfigLoader`.
The following examples will all make use of the default `ConfigLoader` class.

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")
credentials = conf_loader["credentials"]
```

This will load configuration files from `conf/base` and `conf/local` whose filenames start with `credentials`, or that are located inside a folder with a name that starts with `credentials`.

```{note}
Since `local` is set as the environment, the configuration path `conf/local` takes precedence in the example above. Hence, any overlapping top-level keys from `conf/base` will be overwritten by the ones from `conf/local`.
```

Calling `conf_loader[key]` in the example above throws a `MissingConfigException` error if no configuration files match the given key. If this is a valid workflow for your application, you can handle it as follows:

```python
from kedro.config import ConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path, env="local")

try:
    credentials = conf_loader["credentials"]
except MissingConfigException:
    credentials = {}
```

```{note}
The `kedro.framework.context.KedroContext` class uses the approach above to load project credentials.
```

Credentials configuration can then be used on its own or [fed into the `DataCatalog`](../data/data_catalog.md#feeding-in-credentials).

### AWS credentials

When you work with AWS credentials on datasets, you are not required to store AWS credentials in the project configuration files. Instead, you can specify them using environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, optionally, `AWS_SESSION_TOKEN`. Please refer to the [official documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.
