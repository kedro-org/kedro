# How to configure your project

This guide shows you how to configure your Kedro project for different scenarios.

## On this page

- [How to change the setting for a configuration source folder](#how-to-change-the-setting-for-a-configuration-source-folder)
- [How to change the configuration source folder at runtime](#how-to-change-the-configuration-source-folder-at-runtime)
- [How to read configuration from a compressed file](#how-to-read-configuration-from-a-compressed-file)
- [How to read configuration from remote storage](#how-to-read-configuration-from-remote-storage)
- [How to access configuration in code](#how-to-access-configuration-in-code)
- [How to load a data catalog with credentials in code](#how-to-load-a-data-catalog-with-credentials-in-code)
- [How to specify additional configuration environments](#how-to-specify-additional-configuration-environments)
- [How to change the default overriding environment](#how-to-change-the-default-overriding-environment)
- [How to use a single configuration environment](#how-to-use-a-single-configuration-environment)
- [How to use a custom configuration loader](#how-to-use-a-custom-configuration-loader)
- [How to change which configuration files are loaded](#how-to-change-which-configuration-files-are-loaded)
- [How to ensure non default configuration files get loaded](#how-to-ensure-non-default-configuration-files-get-loaded)
- [How to bypass the configuration loading rules](#how-to-bypass-the-configuration-loading-rules)
- [How to change the merge strategy used by `OmegaConfigLoader`](#how-to-change-the-merge-strategy-used-by-omegaconfigloader)
- [Advanced configuration without a full Kedro project](#advanced-configuration-without-a-full-kedro-project)

## How to change the setting for a configuration source folder
To store the Kedro project configuration in a different folder to `conf`, change the configuration source by setting the `CONF_SOURCE` variable in [`src/<package_name>/settings.py`](../tutorials/settings.md) as follows:

```python
CONF_SOURCE = "new_conf"
```

## How to change the configuration source folder at runtime
Specify a source folder for the configuration files at runtime using the [`kedro run` CLI command](../getting-started/commands_reference.md#kedro-commands) with the `--conf-source` flag as follows:

```bash
kedro run --conf-source=<path-to-new-conf-folder>
```

## How to read configuration from a compressed file
You can read configuration from a compressed file in `tar.gz` or `zip` format by using the [kedro.config.OmegaConfigLoader][].

How to reference a `tar.gz` file:

```bash
kedro run --conf-source=<path-to-compressed-file>.tar.gz
```

How to reference a `zip` file:

```bash
kedro run --conf-source=<path-to-compressed-file>.zip
```

To compress your configuration you can use Kedro's `kedro package` command. This builds the package into the `dist/` folder of your project, creating a `.whl` file and a `tar.gz` file containing the project configuration. The compressed version of the config files excludes any files inside your `local` folder.

You can also run the command below to create a `tar.gz` file:

```bash
tar --exclude=local/*.yml -czf <my_conf_name>.tar.gz --directory=<path-to-conf-dir> <conf-dir>
```

Or the following command to create a `zip` file:

```bash
zip -x <conf-dir>/local/** -r <my_conf_name>.zip <conf-dir>
```

For both the `tar.gz` and `zip` file, the following structure is expected:

```text
<conf_dir>
├── base               <-- the files inside may be different, but this is an example of a standard Kedro structure.
│   └── parameters.yml
│   └── catalog.yml
└── local              <-- the top level local folder is required, but no files should be inside when distributed.
└── README.md          <-- optional but included with the default Kedro conf structure.
```

## How to read configuration from remote storage
You can read configuration from remote storage locations using cloud storage protocols. This allows you to separate your configuration from your code and securely store different configurations for various environments or tenants.

Supported protocols include:
- Amazon S3 (`s3://`)
- Azure Blob Storage (`abfs://`, `abfss://`)
- Google Cloud Storage (`gs://`, `gcs://`)
- HTTP/HTTPS (`http://`, `https://`)
- And other protocols supported by `fsspec`

To use a remote configuration source, specify the URL when running your Kedro pipeline:

```bash
# Amazon S3
kedro run --conf-source=s3://my-bucket/configs/

# Azure Blob Storage
kedro run --conf-source=abfs://container@account/configs/

# Google Cloud Storage
kedro run --conf-source=gs://my-bucket/configs/
```

### Authentication for remote configuration
Authentication for remote configuration sources must be set up through environment variables or other credential mechanisms provided by the cloud platform. Unlike datasets in the data catalog, you cannot use credentials from `credentials.yml` for remote configuration sources since those credentials would be part of the configuration you're trying to access.

**Examples of authentication setup:**

Amazon S3:
```bash
  export AWS_ACCESS_KEY_ID=your_access_key
  export AWS_SECRET_ACCESS_KEY=your_secret_key
  kedro run --conf-source=s3://my-bucket/configs/
```
Google Cloud Storage:
```
gcloud auth application-default login
kedro run --conf-source=gs://my-bucket/configs/
```
Azure Blob Storage:
```
export AZURE_STORAGE_ACCOUNT=your_account_name
export AZURE_STORAGE_KEY=your_account_key
kedro run --conf-source=abfs://container@account/configs/
```
For more detailed authentication instructions, see the documentation of your cloud provider.

The remote storage should maintain the same configuration structure as local configuration, with appropriate `base` and environment folders:

```text
s3://my-bucket/configs/
├── base/
│   ├── catalog.yml
│   └── parameters.yml
└── prod/
    └── parameters.yml
```

!!! note
    Kedro supports reading configuration from compressed files (.tar.gz, .zip) and from cloud storage separately. It does not support reading compressed files directly from cloud storage (for example, s3://my-bucket/configs.tar.gz).

## How to access configuration in code
To directly access configuration in code, for example to debug, you can do so as follows:

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

# Instantiate an `OmegaConfigLoader` instance with the location of your project configuration.
conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

# This line shows how to access the catalog configuration. You can access other configuration in the same way.
conf_catalog = conf_loader["catalog"]
```

## How to load a data catalog with credentials in code
!!! note
    We do not recommend that you load and manipulate a data catalog directly in a Kedro node. Nodes are designed to be pure functions and thus should remain agnostic of I/O.

Assuming your project contains a catalog and credentials file in `base` and `local` environments respectively, you can use the `OmegaConfigLoader` to load these configurations. Pass them to a `DataCatalog` object to access the catalog entries with resolved credentials.
```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings
from kedro.io import DataCatalog

# Instantiate an `OmegaConfigLoader` instance with the location of your project configuration.
conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(
    conf_source=conf_path, base_env="base", default_run_env="local"
)

# These lines show how to access the catalog and credentials configurations.
conf_catalog = conf_loader["catalog"]
conf_credentials = conf_loader["credentials"]

# Fetch the catalog with resolved credentials from the configuration.
catalog = DataCatalog.from_config(catalog=conf_catalog, credentials=conf_credentials)
```

## How to specify additional configuration environments
Besides the two built-in `local` and `base` configuration environments, you can create your own. Your project loads `conf/base/` as the bottom-level configuration environment but allows you to overwrite it with any other environments that you create, such as `conf/server/` or `conf/test/`. To use additional configuration environments, run the following command:

```bash
kedro run --env=<your-environment>
```

If no `env` option is specified, this will default to using the `local` environment to overwrite `conf/base`.

If you set the `KEDRO_ENV` environment variable to the name of your environment, Kedro will load that environment for your `kedro run`, `kedro ipython`, `kedro jupyter notebook` and `kedro jupyter lab` sessions:

```bash
export KEDRO_ENV=<your-environment>
```

!!! note
    If you both specify the `KEDRO_ENV` environment variable and provide the `--env` argument to a CLI command, the CLI argument takes precedence.

## How to change the default overriding environment
By default, `local` is the overriding environment for `base`. To change the folder, customise the configuration loader argument settings in `src/<package_name>/settings.py` and set the `CONFIG_LOADER_ARGS` key to have a new `default_run_env` value.

For example, if you want to override `base` with configuration in a custom environment called `prod`, you change the configuration loader arguments in `settings.py` as follows:

```python
CONFIG_LOADER_ARGS = {"default_run_env": "prod"}
```

## How to use a single configuration environment
Customise the configuration loader arguments in `settings.py` as follows if your project does not have any other environments apart from `base` (that is, no `local` environment to default to):

```python
CONFIG_LOADER_ARGS = {"default_run_env": "base"}
```

## How to use a custom configuration loader

You can build a custom configuration loader by extending the [kedro.config.AbstractConfigLoader][] class:

```python
from kedro.config import AbstractConfigLoader


class CustomConfigLoader(AbstractConfigLoader):
    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
    ):
        super().__init__(
            conf_source=conf_source, env=env, runtime_params=runtime_params
        )

        # Custom implementation
```
To use this custom configuration loader, set it as the project configuration loader in `src/<package_name>/settings.py` as follows:
```python
from package_name.custom_configloader import CustomConfigLoader

CONFIG_LOADER_CLASS = CustomConfigLoader
```

## How to change which configuration files are loaded

If you want to change the patterns that the configuration loader uses to find the files to load you need to set the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../tutorials/settings.md).
For example, if your `parameters` files are using a `params` naming convention instead of `parameters` (for example, `params.yml`) you need to update `CONFIG_LOADER_ARGS` as follows:

```python
CONFIG_LOADER_ARGS = {
    "config_patterns": {
        "parameters": ["params*", "params*/**", "**/params*"],
    }
}
```

By changing this setting, the default behaviour for loading parameters will be replaced, while the other configuration patterns will remain in their default state.

## How to ensure non default configuration files get loaded

You can add configuration patterns to match files other than `parameters`, `credentials`, and `catalog` by setting the `CONFIG_LOADER_ARGS` variable in [`src/<package_name>/settings.py`](../tutorials/settings.md).
For example, if you want to load Spark configuration files you need to update `CONFIG_LOADER_ARGS` as follows:

```python
CONFIG_LOADER_ARGS = {
    "config_patterns": {
        "spark": ["spark*/"],
    }
}
```

## How to bypass the configuration loading rules

You can bypass the configuration patterns and set configuration directly on the instance of a config loader class. You can bypass the default configuration (catalog, parameters, and credentials) as well as additional configuration.

For example, you can [use hooks to load external credentials](../extend/hooks/common_use_cases.md#use-hooks-to-load-external-credentials).

If you are using a config loader as a standalone component, you can override configuration as follows:

```python
:lineno-start: 10
:emphasize-lines: 8

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

# Bypass configuration patterns by setting the key and values directly on the config loader instance.
conf_loader["catalog"] = {"catalog_config": "something_new"}
```

## How to change the merge strategy used by `OmegaConfigLoader`

By default, `OmegaConfigLoader` merges configuration [in different environments](configuration_explanation.md#configuration-environments) as well as runtime parameters in a destructive way. This means that whatever configuration resides in your overriding environment (`local` by default) takes precedence when the same top-level key is present in the base and overriding environment. Any configuration for that key **besides that given in the overriding environment** is discarded.
The same behaviour applies to runtime parameters overriding any configuration in the `base` environment.
You can change the merge strategy for each configuration type in your project's `src/<package_name>/settings.py`. The accepted merging strategies are `soft` and `destructive`.

```python
from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader

CONFIG_LOADER_ARGS = {
    "merge_strategy": {
        "parameters": "soft",
        "spark": "destructive",
        "mlflow": "soft",
    }
}
```

If no merge strategy is defined, the default destructive strategy will be applied. **Note**: this merge strategy setting applies when configuration files are located in **different** environments.
When files are part of the same environment, they are always merged in a soft way. An error is thrown when files in the same environment contain the same top-level keys.

## Advanced configuration without a full Kedro project

In some cases, you may want to use the `OmegaConfigLoader` without a Kedro project. By default, a Kedro project has a `base` and `local` environment.
When you use the `OmegaConfigLoader` directly, it assumes *no* environment. You may find it useful to [add Kedro to your existing notebooks](../integrations-and-plugins/notebooks_and_ipython/notebook-example/add_kedro_to_a_notebook.md).

### Read configuration

The config loader can work without a Kedro project structure.
```bash
tree .
.
└── parameters.yml
```

Consider the following `parameters.yml` file and example Python script:

```yaml
learning_rate: 0.01
train_test_ratio: 0.7
```

```python
from kedro.config import OmegaConfigLoader
config_loader = OmegaConfigLoader(conf_source=".")

# Optionally, you can also use environments
# config_loader = OmegaConfigLoader(conf_source=".", base_env="base", default_run_env="local")

print(config_loader["parameters"])
```

If you run it from the same directory where `parameters.yml` placed it gives the following output:

```console
{'learning_rate': 0.01, 'train_test_ratio': 0.7}
```

### How to ignore hidden files and directories with `OmegaConfigLoader`

The `OmegaConfigLoader` provides an option to ignore hidden files and directories (those starting with a dot, for example, `.hidden_file` or `.hidden_folder`) when loading configuration files. This behaviour is controlled by the `ignore_hidden` parameter, which is set to `True` by default.

If you want to include hidden files and directories in your configuration loading process, you can set `ignore_hidden` to False when instantiating the `OmegaConfigLoader`:

```py
from kedro.config import OmegaConfigLoader

conf_loader = OmegaConfigLoader(conf_source="conf", ignore_hidden=False)
```
