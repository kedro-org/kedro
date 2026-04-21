# How to configure your project

This guide shows you how to configure your Kedro project for different scenarios.

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

To compress your configuration you can use Kedro's `kedro package` command which builds the package into the `dist/` folder of your project, and creates a `.whl` file, as well as a `tar.gz` file containing the project configuration. The compressed version of the config files excludes any files inside your `local` folder.

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
    While Kedro supports reading configuration from compressed files (.tar.gz, .zip) and from cloud storage separately, it does not support reading compressed files directly from cloud storage (for example, s3://my-bucket/configs.tar.gz).

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

Assuming your project contains a catalog and credentials file, each located in `base` and `local` environments respectively, you can use the `OmegaConfigLoader` to load these configurations, and pass them to a `DataCatalog` object to access the catalog entries with resolved credentials.
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
