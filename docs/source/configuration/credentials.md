# Credentials

For security reasons, we strongly recommend that you *do not* commit any credentials or other secrets to version control.
Kedro is set up so that, by default, if a file inside the `conf` folder (and its subfolders) contains `credentials` in its name, it will be ignored by git.

Credentials configuration can be used on its own directly in code or [fed into the `DataCatalog`](../data/data_catalog.md#dataset-access-credentials).
If you would rather store your credentials in environment variables instead of a file, you can use the `OmegaConfigLoader` [to load credentials from environment variables](advanced_configuration.md#how-to-load-credentials-through-environment-variables) as described in the advanced configuration chapter.

## How to load credentials in code

Credentials configuration can be loaded the same way as any other project configuration using the configuration loader class `OmegaConfigLoader`.


```python
from pathlib import Path

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

# Substitute <project_root> with the [root folder for your project](https://docs.kedro.org/en/stable/tutorial/spaceflights_tutorial.html#terminology)
conf_path = str(Path(<project_root>) / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)
credentials = conf_loader["credentials"]
```

This loads configuration files from `conf/base` and `conf/local` whose filenames start with `credentials`, or that are located inside a folder with a name that starts with `credentials`.

Calling `conf_loader[key]` in the example above throws a `MissingConfigException` error if no configuration files match the given key. But if this is a valid workflow for your application, you can handle it as follows:

```python
from pathlib import Path

from kedro.config import OmegaConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(Path(<project_root>) / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

try:
    credentials = conf_loader["credentials"]
except MissingConfigException:
    credentials = {}
```

```{note}
The `kedro.framework.context.KedroContext` class uses the approach above to load project credentials.
```

## How to work with AWS credentials

When you work with AWS credentials on datasets, you are not required to store AWS credentials in the project configuration files. Instead, you can specify them using environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, optionally, `AWS_SESSION_TOKEN`. See the [official AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.
