# Configuration Reference

## Resolver Syntax

### globals

Access global variables defined in `globals.yml`:

```yaml
${globals:key}
${globals:nested.key}
${globals:key, default_value}
```

**Available in:** All configuration types
**Defined in:** `globals.yml` files
**Example:**

```yaml
# globals.yml
bucket_name: "my-bucket"

# catalog.yml
filepath: "s3://${globals:bucket_name}/data.csv"
```

### runtime_params

Access parameters provided via `--params` CLI option:

```yaml
${runtime_params:key}
${runtime_params:key, default_value}
```

**Available in:** All configuration types except `globals`
**Provided via:** `--params` CLI flag
**Example:**

```yaml
# parameters.yml
random_state: "${runtime_params:seed, 42}"
```

```bash
kedro run --params="seed=123"
```

### oc.env

Load values from environment variables:

```yaml
${oc.env:VARIABLE_NAME}
${oc.env:VARIABLE_NAME, default_value}
```

**Available in:** `credentials.yml` only (by default)
**Example:**

```yaml
# credentials.yml
api_key: ${oc.env:API_KEY}
```

### oc.select

Select a value with a default fallback:

```yaml
${oc.select:key, default_value}
```

**Example:**

```yaml
user: ${oc.select:admin_user, default_admin}
```

### Custom resolvers

Define in `settings.py`:

```python
CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "today": lambda: date.today().isoformat(),
        "add": lambda *values: sum(values),
    }
}
```

Use in configuration:

```yaml
date: "${today:}"
total: "${add:10,20,30}"
```

## Configuration API

### Settings Variables

**CONF_SOURCE**

```python
# src/my_project/settings.py
CONF_SOURCE = "config"  # Default: "conf"
```

**CONFIG_LOADER_CLASS**

```python
from kedro.config import OmegaConfigLoader

CONFIG_LOADER_CLASS = OmegaConfigLoader  # Default
```

**CONFIG_LOADER_ARGS**

```python
CONFIG_LOADER_ARGS = {
    "base_env": "base",              # Default: "base"
    "default_run_env": "local",      # Default: "local"
    "config_patterns": {...},         # Custom file patterns
    "custom_resolvers": {...},        # Custom resolvers
    "merge_strategy": {...},          # Merge strategies by config type
}
```

### OmegaConfigLoader Constructor

```python
from kedro.config import OmegaConfigLoader

conf_loader = OmegaConfigLoader(
    conf_source="conf",              # Required
    base_env="base",                 # Optional
    default_run_env="local",         # Optional
    custom_resolvers={},             # Optional
    config_patterns={},              # Optional
    merge_strategy={},               # Optional
    ignore_hidden=True,              # Optional
)
```

### Default Configuration Patterns

```python
{
    "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
    "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
    "logging": ["logging*", "logging*/**", "**/logging*"],
}
```

### Merge Strategy Options

- `"destructive"` (default): Override environment replaces base completely
- `"soft"`: Deep merge, preserving all keys

```python
CONFIG_LOADER_ARGS = {
    "merge_strategy": {
        "parameters": "soft",
        "catalog": "destructive",
    }
}
```

## Common Exceptions

### MissingConfigException

Raised when configuration files don't exist:

```python
from kedro.config import MissingConfigException

try:
    config = conf_loader["nonexistent"]
except MissingConfigException:
    config = {}
```

### ParserError

Raised when configuration files have syntax errors (from `omegaconf`).

### InterpolationKeyError

Raised when template values are missing (from `omegaconf`):

```yaml
# Missing _bucket_name definition
filepath: "${_bucket_name}/data.csv"  # Raises InterpolationKeyError
```

### ValueError

Raised when duplicate top-level keys exist in the same environment.

## Remote Storage Protocols

| Protocol | URL Format | Authentication |
|----------|------------|----------------|
| Amazon S3 | `s3://bucket/path` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Azure Blob | `abfs://container@account/path` | `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY` |
| Google Cloud | `gs://bucket/path` | `gcloud auth application-default login` |
| HTTP/HTTPS | `https://example.com/config` | N/A |

## Configuration Loading Order

1. Load `conf/base/`
2. Load override environment (e.g., `conf/local/` or `--env` specified)
3. Merge configurations according to merge strategy
4. Apply runtime parameters from `--params`

## Reserved Keys and Files

- Files/keys starting with `_` are hidden
- Hidden keys don't appear in loaded configuration
- Hidden keys don't trigger duplication errors
- Useful for YAML anchors and catalog templates
