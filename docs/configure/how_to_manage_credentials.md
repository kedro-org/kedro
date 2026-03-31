# Manage Credentials

## Store credentials in local environment

Create `conf/local/credentials.yml`:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: <your_access_key_id>
    aws_secret_access_key: <your_secret_access_key>

my_database:
  username: <your_username>
  password: <your_password>
```

!!! warning
    - Never commit `conf/local/` to version control
    - Files with "credentials" in the name are automatically gitignored
    - Never store credentials in `conf/base/`

## Use credentials in the data catalog

Reference credentials in `conf/base/catalog.yml`:

```yaml
companies:
  type: pandas.SQLTableDataset
  credentials: my_database
  table_name: companies

my_s3_data:
  type: pandas.CSVDataset
  filepath: s3://my-bucket/data.csv
  credentials: dev_s3
```

Kedro automatically resolves credentials when loading datasets.

## Load credentials in code

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)
credentials = conf_loader["credentials"]
```

Handle cases where credentials might not exist:

```python
from kedro.config import OmegaConfigLoader, MissingConfigException
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

try:
    credentials = conf_loader["credentials"]
except MissingConfigException:
    credentials = {}
```

!!! note
    The `KedroContext` class uses this approach to load project credentials.

## Load catalog with credentials in code

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings
from kedro.io import DataCatalog

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(
    conf_source=conf_path,
    base_env="base",
    default_run_env="local"
)

conf_catalog = conf_loader["catalog"]
conf_credentials = conf_loader["credentials"]

catalog = DataCatalog.from_config(
    catalog=conf_catalog,
    credentials=conf_credentials
)
```

## Use environment variables for credentials

Load credentials from environment variables using `${oc.env:}`:

```yaml
# conf/local/credentials.yml
dev_s3:
  client_kwargs:
    aws_access_key_id: ${oc.env:AWS_ACCESS_KEY_ID}
    aws_secret_access_key: ${oc.env:AWS_SECRET_ACCESS_KEY}
```

Then set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
kedro run
```

!!! note
    The `oc.env` resolver only works in `credentials.yml` by default, not in other configuration files.

## Work with AWS credentials

AWS credentials can be provided via environment variables without storing in files:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_SESSION_TOKEN=your_token  # Optional

kedro run
```

See the [AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for more details.
