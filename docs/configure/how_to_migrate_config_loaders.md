# Migrate from Legacy Config Loaders

`ConfigLoader` and `TemplatedConfigLoader` were removed in Kedro 0.19.0. This guide shows how to migrate to `OmegaConfigLoader`.

## Migrate from ConfigLoader

### 1. Update settings.py

```python
# src/my_project/settings.py
from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader
```

### 2. Update imports

```python
# Before
from kedro.config import ConfigLoader

# After
from kedro.config import OmegaConfigLoader
```

### 3. Update loading syntax

```python
# Before
conf_loader = ConfigLoader(conf_source=conf_path, env="local")
catalog = conf_loader.get("catalog*")

# After
conf_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
catalog = conf_loader["catalog"]
```

The key `"catalog"` points to the default catalog patterns in `OmegaConfigLoader`.

### 4. Update exception handling

```python
# Before: ValueError
# After: MissingConfigException

from kedro.config import MissingConfigException

# Before: BadConfigException
# After: ParserError (from omegaconf.errors)
```

## Migrate from TemplatedConfigLoader

### 1. Update settings.py

```python
# src/my_project/settings.py
from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader
```

### 2. Update imports

```python
# Before
from kedro.config import TemplatedConfigLoader

# After
from kedro.config import OmegaConfigLoader
```

### 3. Update loading syntax

```python
# Before
conf_loader = TemplatedConfigLoader(conf_source=conf_path, env="local")
catalog = conf_loader.get("catalog*")

# After
conf_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
catalog = conf_loader["catalog"]
```

### 4. Update templating syntax

#### Scoped templating (within same config type)

Rename `globals.yml` to match the config pattern:

```bash
# For catalog templates
mv conf/base/globals.yml conf/base/catalog_variables.yml
```

Add `_` prefix to catalog template values:

```yaml
# Before (globals.yml)
bucket_name: "my-s3-bucket"
key_prefix: "my/key/prefix/"

# After (catalog_variables.yml)
_bucket_name: "my-s3-bucket"
_key_prefix: "my/key/prefix/"
```

Update catalog to use `_` prefix:

```yaml
# Before
raw_data:
  filepath: "s3a://${bucket_name}/${key_prefix}/raw/data.csv"

# After
raw_data:
  filepath: "s3a://${_bucket_name}/${_key_prefix}/raw/data.csv"
```

#### Global templating (across config types)

Keep `globals.yml` and use the `globals` resolver:

```yaml
# conf/base/globals.yml (no changes needed)
bucket_name: "my-s3-bucket"
dataset_type:
  csv: "pandas.CSVDataset"
```

Update references to use `${globals:}`:

```yaml
# Before (catalog.yml)
raw_data:
  type: "${dataset_type.csv}"
  filepath: "s3://${bucket_name}/data.csv"

# After (catalog.yml)
raw_data:
  type: "${globals:dataset_type.csv}"
  filepath: "s3://${globals:bucket_name}/data.csv"
```

### 5. Update default value syntax

```yaml
# Before
user: "${write_only_user|ron}"

# After
user: "${oc.select:write_only_user,ron}"
```

### 6. Remove globals_pattern setting

```python
# Remove this from settings.py
CONFIG_LOADER_ARGS = {"globals_pattern": "*globals.yml"}
```

`OmegaConfigLoader` picks up `globals.yml` automatically.

## Update Jinja2 templates

`OmegaConfigLoader` doesn't support Jinja2. Use dataset factories instead:

```yaml
# Before (with Jinja2)
{% for speed in ['fast', 'slow'] %}
{{ speed }}-trains:
  type: MemoryDataset

{{ speed }}-cars:
  type: pandas.CSVDataset
  filepath: s3://${bucket_name}/{{ speed }}-cars.csv
{% endfor %}

# After (with dataset factories)
"{speed}-trains":
  type: MemoryDataset

"{speed}-cars":
  type: pandas.CSVDataset
  filepath: s3://${bucket_name}/{speed}-cars.csv
```

See [dataset factories documentation](../catalog-data/kedro_dataset_factories.md) for more details.

## Exception reference

| Old | New |
|-----|-----|
| `ValueError` (missing config) | `MissingConfigException` |
| `BadConfigException` | `ParserError` |
| N/A | `InterpolationKeyError` (missing template values) |
