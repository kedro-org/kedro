# Kedro Validation Framework

## Overview

The Kedro Validation Framework validates and instantiates typed inputs for pipeline nodes. This framework automatically discovers type requirements from pipeline node signatures using configurable source filters and validates them before they are used, ensuring type safety and early error detection.

## Architecture

The validation framework consists of five main components:

(Extensible to any source type through pluggable source filters but focussing on ParameterValidtor in the POC)

```
KedroContext.params (entry point)
        ↓
ParameterValidator
        ↓
┌─────────────────────┬─────────────────────┐
│ TypeExtractor       │ ModelFactory        │
│ (with SourceFilter) │ (creates instances) │
│  • ParameterFilter  │                     │
│  • DatasetFilter    │                     |
└─────────────────────┴─────────────────────┘
```

### Core Components

1. **ParameterValidator** (`validators/parameter_validator.py`) - Main orchestrator that coordinates parameter validation
2. **TypeExtractor** (`type_extractor.py`) - Discovers type requirements from pipelines using configurable source filter
3. **ModelFactory** (`model_factory.py`) - Creates instances of Pydantic classes and dataclasses
4. **SourceFilters** (`source_filters.py`) - Pluggable filters for different source types (parameters, datasets)
5. **Custom Exceptions** (`exceptions.py`) - Specialized error handling

## Integration Points

### Context-Level Integration

The validation framework integrates directly with `KedroContext.params` property:

```python
@property
def params(self) -> dict[str, Any]:
    """Access validated parameters with automatic type instantiation."""
    return self._get_validated_params()
```

The validation occurs when `context.params` is accessed, providing transparent validation without modifying existing code.

## Parameter Validation Flow

```
┌─────────────────────┐
│ context.params      │
│ accessed            │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐    ┌─────────────────────┐
│ Check cache         │───▶│ Return cached       │
│ (performance opt)   │    │ params              │
└─────────┬───────────┘    └─────────────────────┘
          │ Cache miss
          ▼
┌─────────────────────┐
│ Merge config +      │
│ runtime params      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Extract types using │
│ configured source   │
│ filters             │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐    ┌─────────────────────┐
│ For each param:     │───▶│ ValidationError     │
│ Validate & create   │    │ (on failure)        │
│ typed instance      │    └─────────────────────┘
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Cache results &     │
│ return validated    │
│ parameters          │
└─────────────────────┘
```

## Important Methods

### ParameterValidator

#### `validate_raw_params(config_params: dict, runtime_params: dict) -> dict[str, Any]`
Main entry point for parameter validation. Merges configuration and runtime parameters, then applies validation based on discovered type requirements.

**Parameters:**
- `config_params`: Parameters from configuration files
- `runtime_params`: Parameters passed at runtime

**Returns:** Dictionary of validated and instantiated parameters

**Raises:** `ValidationError` if validation fails

#### `get_pipeline_requirements() -> dict[str, type]`
Discovers all type requirements from registered pipelines using the configured TypeExtractor.

**Returns:** Mapping of source keys to their expected types

### TypeExtractor

The TypeExtractor uses a **source filter architecture** for flexible type extraction from different sources.

#### **Constructor**
```python
TypeExtractor(source_filter: SourceFilter)
```

**Parameters:**
- `source_filter`: A source filter instance for extraction.

#### **Core Methods**

#### `extract_types_from_pipelines() -> dict[str, type]`
Extracts type requirements from all pipelines using configured source filters.

**Returns:** Dictionary mapping source keys to their expected types

#### `extract_types_from_pipeline(pipeline) -> dict[str, type]`
Extracts type requirements from a single pipeline.

**Returns:** Dictionary mapping source keys to their expected types

#### `extract_types_from_node(node) -> dict[str, type]`
Extracts typed requirements from a single node using configured source filters.

**Returns:** Dictionary mapping source keys to their expected types

#### **Source Filter Architecture**

TypeExtractor uses pluggable source filter to determine which sources to process:

```python
from kedro.framework.validation import ParameterSourceFilter

# parameter extraction
type_extractor = TypeExtractor(ParameterSourceFilter())

# dataset extraction
type_extractor = TypeExtractor(DatasetSourceFilter())

# Future: Custom source filters
class ConfigSourceFilter(SourceFilter):
    def should_process(self, source_name: str) -> bool:
        return source_name.startswith("config:")

    def extract_key(self, source_name: str) -> str:
        return source_name.split(":", 1)[1]

    def get_log_message(self, key: str, type_name: str) -> str:
        return f"Found config requirement: {key} -> {type_name}"

# Use custom filter
type_extractor = TypeExtractor(ConfigSourceFilter())
```

#### **Available Source Filters**

- **ParameterSourceFilter**: Processes `params:*` sources (default)
- **DatasetSourceFilter**: Processes non `params:*` sources (placeholder for future)

### ModelFactory

#### `instantiate(self, source_key: str, raw_value: Any, model_type: type) -> Any:`
Creates typed instances from raw parameter values.

**Supported Types:**
- Pydantic BaseModel subclasses
- Python dataclasses
- Built-in types (returned as-is)

### SourceFilters

#### **SourceFilter Interface**
Abstract base class for creating custom source filters.

**Required Methods:**
- `should_process(source_name: str) -> bool`: Determine if this filter processes the source
- `extract_key(source_name: str) -> str`: Extract the key from the source name
- `get_log_message(key: str, type_name: str) -> str`: Generate appropriate log message

#### **Built-in Source Filters**

#### `ParameterSourceFilter`
Processes `params:*` sources for parameter validation.

#### `DatasetSourceFilter`
Processes non `params:*` sources for future dataset validation.

## Examples

### Basic Dataclass Validation

```python
from dataclasses import dataclass
from kedro.pipeline import Pipeline, node

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str

def connect_to_db(db_config: DatabaseConfig) -> str:
    return f"Connected to {db_config.database}@{db_config.host}:{db_config.port}"

# Pipeline definition
pipeline = Pipeline([
    node(
        func=connect_to_db,
        inputs=["params:db_config"],
        outputs="connection_status",
        name="connect_db"
    )
])

# parameters.yml
# db_config:
#   host: localhost
#   port: 5432
#   database: myapp

# The framework automatically creates DatabaseConfig instance
# from the db_config parameters when the pipeline runs
```

### Pydantic Class Validation

```python
from pydantic import BaseModel, validator

class APIConfig(BaseModel):
    endpoint: str
    timeout: int
    retries: int

    @validator('timeout')
    def timeout_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('timeout must be positive')
        return v

def call_api(api_config: APIConfig) -> dict:
    return {"endpoint": api_config.endpoint, "configured": True}

# Pipeline definition
pipeline = Pipeline([
    node(
        func=call_api,
        inputs=["params:api_config"],
        outputs="api_config_status",
        name="connect_api"
    )
])

# parameters.yml
# api_config:
#   endpoint: https://api.example.com
#   timeout: 30
#   retries: 3

# APIConfig instance is automatically created and validated
```

### Nested Parameter Paths

```python
@dataclass
class MLConfig:
    learning_rate: float
    batch_size: int
    epochs: int

@dataclass
class Training:
    ml_params: MLConfig


def train_pipeline(training: Training) -> str:
    return f"Training with lr={training.ml_params.learning_rate}"

# Pipeline definition
pipeline = Pipeline([
    node(
        func=train_pipeline,
        inputs=["params:training"],
        outputs="training_status",
        name="train"
    )
])

# parameters.yml
# training:
#   ml_params:
#     learning_rate: 0.001
#     batch_size: 32
#     epochs: 100

# Training and MLConfig instances are automatically created and validated
```

## Error Handling

### Parameter Validation Errors

```python
# When validation fails:
try:
    params = context.params
except ValidationError as e:
    print(f"Validation failed for source: {e.source_key}")
    print(f"Errors: {e.errors}")
    print(f"Message: {e}")
```

### Generic Exception Design

The validation framework uses generic exceptions that can be reused across different validators:

#### **ValidationError**
- **Purpose**: Generic validation error for any validation scenario
- **Attributes**:
  - `source_key`: The source identifier that failed validation (parameter key, dataset name, etc.)
  - `errors`: List of specific validation error messages
- **Usage**: Base exception for all validation failures

#### **ModelInstantiationError**
- **Purpose**: Specific error for model instantiation failures
- **Inherits**: ValidationError
- **Additional Attributes**:
  - `model_type`: The model type that failed to instantiate
  - `original_error`: The underlying exception that caused the failure
- **Usage**: Raised when Pydantic models, dataclasses, or other model types fail to instantiate


### Common Error Scenarios

1. **Missing Required Parameters**
```
ValidationError: Missing required parameter 'database_config' for dataclass DatabaseConfig
```

2. **Type Validation Failures**
```
ValidationError: Failed to instantiate DatabaseConfig for parameter 'db_config':
field required (type=value_error.missing)
```

3. **Invalid Parameter Values**
```
ValidationError: Failed to instantiate APIConfig for parameter 'api_config':
timeout must be positive (type=value_error)
```

## Performance and Caching

### Intelligent Caching

The framework implements intelligent caching to avoid re-validation:

- **Cache Behavior**: Results are cached for the lifetime of the context object
- **Cache Scope**: Within a single Kedro session, multiple `context.params` calls return cached results
- **Memory Efficiency**: Only caches final validated results

### Cache Behavior

```python
# First access: validation occurs
params1 = context.params  # Validates and caches

# Subsequent access: cached result returned
params2 = context.params  # Returns cached params (params1 is params2 == True)

# New context: validation occurs again
new_context = KedroContext(...)
params3 = new_context.params  # Re-validates and caches in new context
```

## Configuration

### Disabling Validation

The validation framework can be disabled by ensuring no typed parameters are required by pipeline nodes, or by using only built-in types in node signatures.

### Error Handling

The framework raises validation errors by default:
- All validation errors cause immediate failure
- No fallback to raw parameter values
- Ensures type safety throughout the pipeline

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Problem**: `ImportError: No module named 'kedro.framework.project'`
**Solution**: Ensure you're running within a Kedro project context

#### 2. Type Discovery Failures
**Problem**: Parameters not being validated despite type hints
**Solution**:
- Verify pipeline is registered in `kedro.framework.project.pipelines`
- Check that type hints are properly defined in node functions
- Ensure parameter names match between configuration and function signatures

#### 3. Validation Performance
**Problem**: Slow parameter access
**Solution**:
- Validation results are cached automatically
- Consider simplifying complex type validation logic
- Check for unnecessary nested parameter structures

#### 4. Parameter Path Resolution
**Problem**: Nested parameters not found
**Solution**:
- Verify parameter structure in configuration files
- Check that parameter names exactly match function argument names
- Use dot notation for nested parameter access if needed

### Debugging Tips

1. **Enable Detailed Logging**
```python
import logging
logging.getLogger("kedro.framework.validation").setLevel(logging.DEBUG)
```

2. **Check Pipeline Requirements**
```python
from kedro.framework.validation.validators import ParameterValidator

parameter_validator = ParameterValidator()
requirements = parameter_validator.get_pipeline_requirements()
print("Discovered requirements:", requirements)
```

3. **Validate Individual Parameters**
```python
from kedro.framework.validation import ModelFactory

factory = ModelFactory()
try:
    result = factory.instantiate("test_param", raw_value, target_type)
    print("Validation successful:", result)
except Exception as e:
    print("Validation failed:", e)
```

## Future Extensibility

The validation framework is designed with extensibility in mind, allowing it to be used beyond just parameter validation:

### Architecture Design

The core components are designed to be generic and reusable:

#### **TypeExtractor with Source Filter**
- **Current Use**: Extracts parameter types using `ParameterSourceFilter`
- **Architecture**: Uses pluggable source filter for flexible type extraction
- **Future Potential**: Can easily support new source types by adding source filter:
  - `DatasetSourceFilter` for dataset schema extraction
  - `ConfigSourceFilter` for configuration validation schemas
  - `APISourceFilter` for API endpoint specifications
  - Custom source filter for any validation scenario

#### **ModelFactory**
- **Current Use**: Instantiates Pydantic models and dataclasses for parameters
- **Future Potential**: Can be extended to instantiate:
  - Pandera schemas for dataset validation
  - JSONSchema validators for configuration
  - Custom validation models for different data sources

### Example Future Usage

The same components could power additional validators:

```python
# Create custom source filter for datasets
class DatasetSourceFilter(SourceFilter):
    """Filter for dataset sources (future implementation)."""

    def should_process(self, source_name: str) -> bool:
        """Check if source is a dataset source."""
        # Future: check for dataset patterns like "dataset:" prefix
        return isinstance(source_name, str) and not source_name.startswith("params:")

    def extract_key(self, source_name: str) -> str:
        """Extract dataset key from dataset:key format."""
        # Future: extract dataset key
        return source_name

    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate dataset-specific log message."""
        return f"Found dataset requirement: {key} -> {type_name}"

# Future DatasetValidator using source filter architecture
class DatasetValidator:
    def __init__(self):
        # Use TypeExtractor with DatasetSourceFilter
        self.type_extractor = TypeExtractor(DatasetSourceFilter())
        self.model_factory = ModelFactory()
        self.logger = logging.getLogger(__name__)

    def validate_dataset_schema(self, data: Any) -> Any:
        # Extract schema requirements from pipelines (dataset:* sources)
        schema_requirements = self.type_extractor.extract_types_from_pipelines()

        # Apply validation using discovered schema types
        # ... validation logic ...
        return data

# Future ConfigValidator with custom source filter
class ConfigSourceFilter(SourceFilter):
    def should_process(self, source_name: str) -> bool:
        return source_name.startswith("config:")

    def extract_key(self, source_name: str) -> str:
        return source_name.split(":", 1)[1]

    def get_log_message(self, key: str, type_name: str) -> str:
        return f"Found config requirement: {key} -> {type_name}"

class ConfigValidator:
    def __init__(self):
        # Use TypeExtractor with ConfigSourceFilter
        self.type_extractor = TypeExtractor(ConfigSourceFilter())
        self.model_factory = ModelFactory()

    def validate_app_config(self, config: dict) -> dict:
        # Extract config requirements from pipelines (config:* sources)
        config_requirements = self.type_extractor.extract_types_from_pipelines()

        # Apply validation using discovered config types
        # ... validation logic ...
        return config
```

This design ensures that as Kedro's validation needs grow, the same components can be leveraged for different validation scenarios while maintaining consistency and reliability.

## Best Practices

1. **Type Hint Consistency**: Ensure all node functions have clear type hints for parameters
2. **Parameter Naming**: Use consistent parameter names between configuration and function signatures
3. **Validation Logic**: Keep validation logic simple and focused on data integrity
4. **Error Handling**: Implement proper error handling in calling code for validation failures
5. **Configuration Structure**: Organize parameters logically in configuration files to match expected types
