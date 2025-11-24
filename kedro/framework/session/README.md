# Kedro Parameter Validation System

This document describes the parameter validation system integrated into Kedro sessions, which provides automatic validation and instantiation of structured parameter objects from configuration files.

## Overview

The parameter validation system consists of two complementary hooks that work together to ensure parameter integrity:

1. **`KedroParameterHook`** - Always active, handles parameter processing during pipeline execution
2. **`KedroValidationHook`** - Optional, provides upfront validation when `--validate` flag is used

## Architecture

### Core Components

```
kedro/framework/session/
├── validator.py          # Parameter validation hooks and utilities
├── session.py           # Modified to integrate validation hooks
└── README.md           # This documentation
```

### Shared Utilities (`ParameterModelUtils`)

The `ParameterModelUtils` class provides common functionality used by both hooks:

- **Parameter extraction** from nested configurations
- **Type hint analysis** from node function signatures
- **Object instantiation** for Pydantic and dataclass types
- **Error handling** with optional warning mechanisms

## How It Works

### 1. Without Validation (`kedro run`)

When running without the `--validate` flag:

```python
# Only KedroParameterHook is registered
parameter_hook = KedroParameterHook()
hook_manager.register(parameter_hook)
```

**Flow:**
1. `after_context_created` stores context parameters
2. `before_node_run` analyzes each node's requirements
3. Attempts to instantiate typed objects from raw parameters
4. Logs warnings for failed instantiation, falls back to raw dictionaries
5. Caches successful instantiations for reuse

### 2. With Validation (`kedro run --validate`)

When running with the `--validate` flag:

```python
# Both hooks are registered with shared state
parameter_hook = KedroParameterHook()
validation_hook = KedroValidationHook(parameter_hook)
hook_manager.register(parameter_hook)
hook_manager.register(validation_hook)
```

**Flow:**
1. `KedroValidationHook.after_context_created` runs first:
   - Validates all parameters across all pipelines
   - Fails fast if validation errors occur
   - Shares validated objects with parameter hook
2. `KedroParameterHook.after_context_created` stores context parameters
3. `KedroParameterHook.before_node_run` uses pre-validated objects

## Examples

### Basic Configuration Setup

**conf/base/parameters.yml:**
```yaml
database:
  host: "localhost"
  port: 5432
  name: "analytics"
  ssl_enabled: true

api:
  endpoint: "https://api.example.com"
  timeout: 30
  retries: 3
```

### Dataclass Definition

```python
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    ssl_enabled: bool = False

@dataclass
class ApiConfig:
    endpoint: str
    timeout: int = 30
    retries: int = 3
```

### Pydantic Definition

```python
from pydantic import BaseModel, HttpUrl

class DatabaseConfig(BaseModel):
    host: str
    port: int = 5432
    name: str
    ssl_enabled: bool = False

class ApiConfig(BaseModel):
    endpoint: HttpUrl
    timeout: int = 30
    retries: int = 3
```

### Node Function with Type Hints

```python
from kedro import node
from kedro.pipeline import Pipeline

def process_data(
    db_config: DatabaseConfig,
    api_config: ApiConfig,
    raw_data: pd.DataFrame
) -> pd.DataFrame:
    # Function receives validated configuration objects
    connection = connect_to_db(
        host=db_config.host,
        port=db_config.port,
        database=db_config.name,
        ssl=db_config.ssl_enabled
    )
    # Process data using configurations
    return processed_data

def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        node(
            func=process_data,
            inputs=[
                "params:database",    # Becomes DatabaseConfig object
                "params:api",         # Becomes ApiConfig object
                "raw_data"
            ],
            outputs="processed_data",
            name="process_data_node"
        )
    ])
```

### Nested Parameters

**conf/base/parameters.yml:**
```yaml
project:
  database:
    host: "prod-db.example.com"
    port: 5432
  cache:
    redis_url: "redis://localhost:6379"
    ttl: 3600
```

```python
@dataclass
class CacheConfig:
    redis_url: str
    ttl: int = 3600

def analyze_data(
    db_config: DatabaseConfig,
    cache_config: CacheConfig,
    input_data: pd.DataFrame
) -> dict:
    # Access nested configuration objects
    pass

# In pipeline definition:
node(
    func=analyze_data,
    inputs=[
        "params:project.database",  # Nested parameter access
        "params:project.cache",
        "input_data"
    ],
    outputs="analysis_results"
)
```

## Session Integration

The `session.py` file has been modified to automatically register the validation hooks:

```python
# In KedroSession.__init__()

# Always register the parameter hook for before_node_run functionality
from .validator import KedroParameterHook
parameter_hook = KedroParameterHook()
hook_manager.register(parameter_hook)

# Register parameter validation hook only if validation is enabled
if enable_validation:
    from .validator import KedroValidationHook
    # Share the validated_models dictionary between hooks
    validation_hook = KedroValidationHook(parameter_hook)
    hook_manager.register(validation_hook)
```

## Command Line Usage

### Standard Execution
```bash
# Parameters processed during node execution with warnings for failures
kedro run

# Run specific pipeline
kedro run --pipeline data_processing

# Run with tags
kedro run --tags preprocessing
```

### With Validation
```bash
# Validate all parameters upfront, fail fast on validation errors
kedro run --validate

# Validate specific pipeline
kedro run --validate --pipeline data_processing

# Validate with environment
kedro run --validate --env production
```

## Error Handling

### Validation Disabled Behavior

When validation is disabled, parameter instantiation failures are handled gracefully:

```python
# If DatabaseConfig instantiation fails:
# 1. Warning is logged: "Parameter validation warning: Failed to instantiate
#    DatabaseConfig for param 'database': missing required field 'host'.
#    Falling back to raw dictionary."
# 2. Node receives raw dictionary instead of typed object
# 3. Execution continues normally
```

### Validation Enabled Behavior

When validation is enabled, failures cause immediate termination:

```bash
$ kedro run --validate
Parameter validation failed:
- param=database: Failed to instantiate DatabaseConfig for param 'database': field required
- param=api.timeout: Failed to instantiate ApiConfig for param 'api': field required
```

## Benefits

### Type Safety
- Functions receive properly typed configuration objects
- IDE autocompletion and type checking support
- Runtime validation of parameter structure

### Performance
- Objects instantiated once and reused across nodes
- No duplicate validation when both hooks are active
- Efficient caching of validated parameters

### Developer Experience
- Clear error messages for configuration issues
- Graceful fallback when validation disabled
- Support for both Pydantic and dataclass patterns

### Flexibility
- Works with existing Kedro parameter patterns
- Optional validation via command-line flag
- Backward compatible with dictionary-based parameters

## Advanced Usage

### Custom Validation Logic

```python
from pydantic import BaseModel, validator

class DatabaseConfig(BaseModel):
    host: str
    port: int
    name: str
    ssl_enabled: bool = False

    @validator('port')
    def port_must_be_valid(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Database name cannot be empty')
        return v
```

### Environment-Specific Configurations

**conf/base/parameters.yml:**
```yaml
database:
  host: "localhost"
  port: 5432
  name: "dev_db"
```

**conf/production/parameters.yml:**
```yaml
database:
  host: "prod-db.company.com"
  port: 5432
  name: "production_db"
  ssl_enabled: true
```

### Complex Nested Structures

```python
@dataclass
class SecurityConfig:
    encryption_key: str
    token_expiry: int

@dataclass
class DatabaseConfig:
    host: str
    port: int
    security: SecurityConfig

# parameters.yml:
database:
  host: "secure-db.example.com"
  port: 5432
  security:
    encryption_key: "secret-key-here"
    token_expiry: 3600
```

## Troubleshooting

### Common Issues

1. **Missing Type Hints**
   ```python
   # Wrong - no type hint
   def process_data(config, data):
       pass

   # Correct - with type hint
   def process_data(config: DatabaseConfig, data: pd.DataFrame):
       pass
   ```

2. **Parameter Name Mismatch**
   ```python
   # parameters.yml has 'database' but node expects 'db_config'
   inputs=["params:database"]  # Should match parameter name in config
   ```

3. **Invalid Configuration Structure**
   ```yaml
   # Wrong - string instead of object
   database: "localhost:5432"

   # Correct - structured object
   database:
     host: "localhost"
     port: 5432
   ```

### Debug Tips

- Use `kedro run --validate` to catch configuration issues early
- Check log output for parameter validation warnings
- Verify parameter names match between configuration and node inputs
- Ensure dataclass/Pydantic definitions match configuration structure

## Migration Guide

### From Dictionary Parameters

**Before:**
```python
def process_data(params: dict, data: pd.DataFrame):
    db_host = params["database"]["host"]
    db_port = params["database"]["port"]
    # Manual parameter access
```

**After:**
```python
@dataclass
class DatabaseConfig:
    host: str
    port: int

def process_data(db_config: DatabaseConfig, data: pd.DataFrame):
    # Type-safe parameter access
    connection = connect(db_config.host, db_config.port)
```

### Gradual Adoption

The system is backward compatible - you can migrate nodes incrementally:

1. Start with `kedro run` (validation disabled)
2. Add type hints to critical nodes
3. Test with `kedro run --validate`
4. Gradually convert remaining nodes

This allows for smooth transition without breaking existing pipelines.
