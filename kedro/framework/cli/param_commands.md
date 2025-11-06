# Kedro Parameter Generation CLI Commands

This document describes two new CLI commands for automating parameter file and schema generation in Kedro projects.

## Commands Overview

- `kedro catalog create-params` - Generate parameter files from pipeline node function signatures
- `kedro catalog create-schema` - Generate JSON schema from Pydantic models and dataclasses

## `kedro catalog create-params`

### Purpose
Automatically generates parameter files by analyzing pipeline node function type hints and default values. This eliminates manual parameter file creation and ensures consistency between code and configuration.

### Usage
```bash
kedro catalog create-params [OPTIONS]
```

### Options
- `--filepath TEXT` - Specify output filepath for the parameter file
- `--overwrite` - Overwrite existing parameter files

### Implementation Details
- Extracts type hints from node function signatures
- Handles Pydantic models and dataclasses
- Generates example values based on type annotations
- Supports nested parameter structures
- Creates YAML parameter files with proper formatting

### Examples

#### Generate parameters for all pipelines
```bash
kedro catalog create-params
```
Creates: `conf/base/parameters.yml`

#### Generate to custom location
```bash
kedro catalog create-params --filepath custom/params.yml --overwrite
```
Creates: `custom/params.yml` (overwrites if exists)

### Output Format
Generated parameter files contain:
- Parameter names matching function arguments
- Type-appropriate default values
- Comments with type information
- Nested structures for complex types

Example output:
```yaml
# Generated parameters from pipeline nodes with default values
model_config:
  learning_rate: 0.0  # float
  epochs: 0  # int
  batch_size: []  # list
  findings: {} # dict

data_processing:
  chunk_size: 0  # int
  normalize: false  # bool
  description: "" # string
```

## `kedro catalog create-schema`

### Purpose
Generates JSON schema from Pydantic models and dataclasses found in pipeline node functions. This schema can be used for parameter validation and UI generation in tools like Kedro-Viz.

### Usage
```bash
kedro catalog create-schema [OPTIONS]
```

### Options
- `--filepath TEXT` - Specify output filepath (default: `.viz/param-schema.json`)
- `--overwrite` - Overwrite existing schema files

### Implementation Details
- Scans pipeline nodes for Pydantic models and dataclasses
- Converts type annotations to JSON schema format
- Handles Optional/Union types
- Supports nested model structures
- Generates comprehensive validation rules

### Examples

#### Generate schema for all pipelines
```bash
kedro catalog create-schema
```
Creates: `.viz/param-schema.json`

#### Generate to custom location
```bash
kedro catalog create-schema --filepath schemas/validation.json --overwrite
```

### Output Format
Generated schema files contain JSON Schema v7 compatible definitions:

```json
{
  "$defs": {
    "DatabaseConfig": {
      "properties": {
        "host": {
          "title": "Host",
          "type": "string"
        },
        "port": {
          "maximum": 65535,
          "minimum": 1,
          "title": "Port",
          "type": "integer"
        },
        "database": {
          "title": "Database",
          "type": "string"
        }
      },
      "required": [
        "host",
        "port",
        "database"
      ],
      "title": "DatabaseConfig",
      "type": "object"
    },
    "MLConfig": {
      "properties": {
        "model_type": {
          "pattern": "^(linear|tree|neural)$",
          "title": "Model Type",
          "type": "string"
        },
        "hyperparams": {
          "additionalProperties": true,
          "title": "Hyperparams",
          "type": "object"
        }
      },
      "required": [
        "model_type",
        "hyperparams"
      ],
      "title": "MLConfig",
      "type": "object"
    },
    "ProjectParams": {
      "properties": {
        "database": {
          "$ref": "#/$defs/DatabaseConfig"
        },
        "ml": {
          "$ref": "#/$defs/MLConfig"
        }
      },
      "required": [
        "database",
        "ml"
      ],
      "title": "ProjectParams",
      "type": "object"
    }
  },
  "properties": {
    "test_size": {
      "description": "Proportion of test split (e.g. 0.2 for 20%)",
      "title": "Test Size",
      "type": "number"
    },
    "random_state": {
      "description": "Random seed for reproducibility",
      "title": "Random State",
      "type": "integer"
    },
    "features": {
      "description": "List of feature names used for training",
      "items": {
        "type": "string"
      },
      "title": "Features",
      "type": "array"
    },
    "project": {
      "$ref": "#/$defs/ProjectParams"
    }
  },
  "required": [
    "test_size",
    "random_state",
    "features",
    "project"
  ],
  "title": "ModelOptions",
  "type": "object"
}
```

## Use Cases

### Parameter File Generation
1. **Initial Setup**: Generate baseline parameter files for new projects
2. **Refactoring**: Update parameter files after changing node signatures
3. **Documentation**: Maintain consistency between code and configuration
4. **Team Collaboration**: Ensure all team members have correct parameter structures

### Schema Generation
1. **Parameter Validation**: Validate parameter files against generated schemas
2. **UI Generation**: Create forms in Kedro-Viz for parameter editing
3. **Documentation**: Generate parameter documentation automatically


## Integration with Kedro Ecosystem

These commands integrate with:
- **Kedro-Viz**: Schema files enable parameter form generation
- **Pipeline Registry**: Analyzes all registered pipelines

## Requirements

- Kedro project with defined pipelines
- Pydantic models or dataclasses for parameters
