# Kedro Parameter Validation System

This document describes the parameter validation system integrated into Kedro sessions, which provides automatic validation and instantiation of structured parameter objects with strict error checking to ensure data integrity.

## Overview

The parameter validation system consists of a single, efficient hook that automatically transforms parameters:

**`KedroParameterValidationHook`** - Always active, automatically instantiates typed parameter objects with strict validation. **Fails fast on any validation errors to ensure complete data integrity.**

## Architecture

### Core Components

```
kedro/framework/session/
├── validator.py          # Parameter validation hooks and utilities
├── session.py           # Modified to integrate validation hooks
└── README.md           # This documentation
```

### Core Validation (`ParameterValidator`)

The `ParameterValidator` class provides the core functionality:

- **Parameter extraction** from nested configurations
- **Type hint analysis** from node function signatures
- **Object instantiation** for Pydantic and dataclass types
- **Direct parameter transformation** in context.params
- **Strict validation** with immediate error reporting on failures

## How It Works

### Automatic Parameter Transformation (`kedro run`)

The system always runs automatically with every Kedro execution:

```python
# Single hook registration - always active
validation_hook = KedroParameterValidationHook()
hook_manager.register(validation_hook)
```

**Flow:**
1. `KedroParameterValidationHook.after_context_created` runs during context creation
2. Analyzes all pipeline nodes to identify parameter requirements
3. Attempts to instantiate typed objects from raw parameter values
4. **Transforms `context.params` directly** to return instantiated objects
5. Raises validation errors for failed instantiation - ensures data integrity
6. **Node functions receive typed objects automatically** - no runtime processing needed!

## ⚠️ Strict Validation Policy

**Data Integrity First**: This system prioritizes data integrity over convenience. If you define typed parameters in your node functions:

- ✅ **All parameters MUST be valid** - No partial validation
- ⚠️ **Any validation error stops execution** - No fallback to raw dictionaries
- 🎯 **Fix configuration issues before running** - Clear error messages guide you
- 🛡️ **Guaranteed type safety** - Node functions always receive correctly typed objects

**Philosophy**: It's better to fail fast with clear errors than to run with invalid data.

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

The `session.py` file has been modified to automatically register the validation hook:

```python
# In KedroSession.__init__()

# Always register parameter validation hook for automatic model instantiation
from .validator import KedroParameterValidationHook
validation_hook = KedroParameterValidationHook()
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

**Important**: Parameter validation and model instantiation happens automatically for all Kedro runs. **Any validation failures will immediately stop execution** with detailed error messages to ensure data integrity.

## Error Handling

### Strict Validation Behavior

Parameter instantiation failures cause immediate execution termination with clear error messages:

```python
# If DatabaseConfig instantiation fails:
# 1. Error is logged: "Parameter validation failed: ..."
# 2. RuntimeError is raised with detailed validation errors
# 3. Execution stops immediately - no partial runs with invalid data
```

### Example Error Output

```bash
$ kedro run
INFO - Successfully instantiated 3 parameter models
ERROR - Parameter validation failed: Parameter validation failed:
- Parameter 'database': Failed to instantiate DatabaseConfig for param 'database': field 'host' required

RuntimeError: Parameter validation failed:
- Parameter 'database': Failed to instantiate DatabaseConfig for param 'database': field 'host' required
```

## Benefits

### Data Integrity
- **Guaranteed valid parameters** - No execution with invalid data
- **Fail-fast validation** - Catch configuration issues before pipeline runs
- **Complete type safety** - All typed parameters are validated or execution stops
- **Consistent behavior** - No mixed states with partially validated parameters

### Performance
- Objects instantiated once during context creation
- Zero runtime overhead during pipeline execution
- Efficient single-pass parameter transformation

### Developer Experience
- **Clear, actionable error messages** for configuration issues
- **Immediate feedback** on parameter validation problems
- **IDE support** with proper type hints and autocompletion
- **Predictable behavior** - validation always works the same way

### Reliability
- Works with existing Kedro parameter patterns
- Automatic operation with no configuration needed
- Strict validation ensures data integrity
- Clear error messages help identify configuration issues

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

- Check error messages for specific validation failures
- Verify parameter names match between configuration and node inputs
- Ensure dataclass/Pydantic definitions match configuration structure
- Look for "Successfully instantiated X parameter models" info messages
- Fix validation errors before pipeline execution can proceed

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

1. Add type hints to functions you want to enhance
2. Run `kedro run` - typed parameters work automatically!
3. Fix any validation errors that are reported
4. Gradually convert remaining nodes

**Important**: Once you add type hints to node parameters, those parameters **must** be valid according to your type definitions, or the pipeline will not run. Existing dictionary-based parameters (without type hints) continue to work normally.
