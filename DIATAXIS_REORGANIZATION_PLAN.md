# Configuration Documentation Reorganization Plan (Diataxis Framework)

> **NOTE**: This file will be removed before merge. It exists solely to help reviewers understand the reorganization and track where content has moved from/to.

## Overview
This plan reorganizes the Configuration documentation to align with the Diataxis framework by separating **Explanation** (understanding-oriented) content from **How-to Guides** (task-oriented) content.

**Key Principle**: NO content changes - only moving sections/paragraphs. The documentation below shows what content moves where, so reviewers can easily verify that content has been preserved, not rewritten.

---

## Proposed New Structure

The reorganization creates:
- **3 Explanation files** (understanding-oriented)
- **6 How-to Guide files** (task-oriented)
- **Migration guide** kept as-is

### Navigation Structure (mkdocs.yml)
```yaml
- Configure:
    - Understanding Configuration:
        - Configuration concepts: configure/configuration_explanation.md
        - Parameters and credentials concepts: configure/parameters_and_credentials_explanation.md
        - Templating concepts: configure/templating_explanation.md
    - How-to Guides:
        - Configure your project: configure/how_to_configure_project.md
        - Work with parameters: configure/how_to_use_parameters.md
        - Validate parameters: configure/how_to_validate_parameters.md
        - Manage credentials: configure/how_to_manage_credentials.md
        - Use advanced configuration: configure/how_to_advanced_configuration.md
        - Migrate config loaders: configure/config_loader_migration.md
```

---

## Detailed Content Mapping

### 1. EXPLANATION: Configuration Concepts (`configuration_explanation.md`)

**Purpose**: Help users understand how Kedro configuration works

**Content to move from `configuration_basics.md`:**

#### Section: Introduction
- [original content moved] Lines 1-9: Title, intro paragraph, note about ConfigLoader deprecation

#### Section: OmegaConfigLoader
- [original content moved] Lines 10-40:
  - What is OmegaConfigLoader
  - What is OmegaConf
  - OmegaConf vs. Kedro's OmegaConfigLoader
  - When to use each

#### Section: Configuration Source
- [original content moved] Lines 42-43: What is the configuration source folder

#### Section: Configuration Environments
- [original content moved] Lines 45-63:
  - What are configuration environments
  - Base environment explanation
  - Local environment explanation

#### Section: Configuration Loading
- [original content moved] Lines 65-78:
  - How Kedro loads configuration
  - Configuration merging rules
  - Hidden keys with underscore

#### Section: Configuration File Names
- [original content moved] Lines 80-87: File name matching rules

#### Section: Configuration Patterns
- [original content moved] Lines 88-102:
  - What are configuration patterns
  - Default patterns for catalog, parameters, credentials, logging
  - How to change patterns (reference to how-to guide)

---

### 2. EXPLANATION: Parameters and Credentials Concepts (`parameters_and_credentials_explanation.md`)

**Purpose**: Help users understand what parameters and credentials are and how they work

**Content to move from `parameters.md`:**

#### Section: Parameters - What are Parameters?
- [original content moved] Lines 1-4:
  - Title
  - Definition of parameters
  - Where they are stored
  - What they are used for

#### Section: Parameters - How Parameters Work
- [original content moved] Lines 6-7: Intro to using parameters for configuration
- [original content moved] Lines 69: How Kedro adds parameters to the Data Catalog as MemoryDatasets

**Content to move from `credentials.md`:**

#### Section: Credentials - What are Credentials?
- [original content moved] Lines 1-7:
  - Title
  - Security warning about not committing credentials
  - How Kedro handles credentials files with git
  - How credentials can be used with DataCatalog

---

### 3. EXPLANATION: Templating Concepts (`templating_explanation.md`)

**Purpose**: Help users understand templating and variable interpolation

**Content to move from `advanced_configuration.md`:**

#### Section: Introduction to Templating
- [new content to be reviewed] Brief intro explaining what templating is and why it's useful

#### Section: How Templating Works with OmegaConfigLoader
- [original content moved] Lines 96-164:
  - How to do templating with the OmegaConfigLoader (conceptual parts)
  - Parameters templating explanation
  - Catalog templating explanation
  - Other configuration files templating explanation
  - Template value loading example

#### Section: Global Variables
- [original content moved] Lines 165-195:
  - Conceptual explanation of globals
  - How globals work across configuration types
  - Globals resolver syntax explanation

#### Section: Runtime Parameters
- [original content moved] Lines 196-248:
  - Conceptual explanation of runtime_params resolver
  - How runtime params override configuration
  - Relationship between globals and runtime_params

#### Section: Resolvers
- [original content moved] Lines 249-311:
  - What are resolvers
  - How resolvers work
  - Built-in resolvers overview

---

### 5. HOW-TO GUIDE: Configure Your Project (`how_to_configure_project.md`)

**Purpose**: Step-by-step guides for common configuration tasks

**Content to move from `configuration_basics.md`:**

#### Introduction
- [new content to be reviewed] Brief intro: "This guide shows you how to configure your Kedro project for different scenarios."

#### How to change the setting for a configuration source folder
- [original content moved] Lines 118-123

#### How to change the configuration source folder at runtime
- [original content moved] Lines 125-130

#### How to read configuration from a compressed file
- [original content moved] Lines 132-170

#### How to read configuration from remote storage
- [original content moved] Lines 172-232

#### How to access configuration in code
- [original content moved] Lines 234-246

#### How to load a data catalog with credentials in code
- [original content moved] Lines 248-270

#### How to specify additional configuration environments
- [original content moved] Lines 272-289

#### How to change the default overriding environment
- [original content moved] Lines 290-297

#### How to use a single configuration environment
- [original content moved] Lines 299-304

---

### 6. HOW-TO GUIDE: Work with Parameters (`how_to_use_parameters.md`)

**Purpose**: Step-by-step guides for working with parameters

**Content to move from `parameters.md`:**

#### Introduction
- [new content to be reviewed] Brief intro about this guide

#### How to use parameters in your pipeline
- [original content moved] Lines 6-68:
  - Basic parameter usage
  - Nested parameter structures
  - Passing all parameters to a node

#### How to load parameters in code
- [original content moved] Lines 72-105

#### How to specify parameters at runtime
- [original content moved] Lines 107-172

#### Parameter validation
- [new content to be reviewed] Brief intro to validation with reference to dedicated guide

---

### 7. HOW-TO GUIDE: Validate Parameters (`how_to_validate_parameters.md`)

**Purpose**: Comprehensive guide to parameter validation with Pydantic and dataclasses

**Content to move from `parameter_validation.md`:**

#### How to validate parameters
- [original content moved] All content from `parameter_validation.md` (Lines 1-303):
  - Introduction
  - Supported types (Pydantic models, dataclasses)
  - How validation works
  - Fail-fast behaviour
  - Pydantic vs. dataclasses
  - Conflicting types across pipelines
  - Optional type hints
  - Known limitations
  - Set up a basic Pydantic model
  - Use field constraints
  - Use nested models
  - Use custom validators
  - Use dataclasses
  - Use multiple typed parameters in one node
  - Mix typed and untyped parameters
  - Use runtime parameters with validation
  - Read validation error messages

---

### 8. HOW-TO GUIDE: Manage Credentials (`how_to_manage_credentials.md`)

**Purpose**: Step-by-step guides for working with credentials

**Content to move from `credentials.md`:**

#### Introduction
- [new content to be reviewed] Brief intro

#### How to load credentials in code
- [original content moved] Lines 9-46

#### How to work with AWS credentials
- [original content moved] Lines 48-51

---

### 9. HOW-TO GUIDE: Use Advanced Configuration (`how_to_advanced_configuration.md`)

**Purpose**: Step-by-step guides for advanced configuration scenarios

**Content to move from `advanced_configuration.md`:**

#### Introduction
- [original content moved] Lines 1-18 (modified to remove conceptual parts)

#### How to use a custom configuration loader
- [original content moved] Lines 21-46

#### How to change which configuration files are loaded
- [original content moved] Lines 49-61

#### How to ensure non default configuration files get loaded
- [original content moved] Lines 63-73

#### How to bypass the configuration loading rules
- [original content moved] Lines 75-94

#### How to load a data catalog with templating in code
- [original content moved] Lines 141-163 (practical code example)

#### How to use global variables with the OmegaConfigLoader
- [original content moved] Lines 165-195 (focus on practical usage, not concepts)

#### How to override configuration with runtime parameters with the OmegaConfigLoader
- [original content moved] Lines 196-248 (focus on practical usage)

#### How to use resolvers in the OmegaConfigLoader
- [original content moved] Lines 249-296 (practical examples)

#### How to load credentials through environment variables
- [original content moved] Lines 312-324

#### How to change the merge strategy used by OmegaConfigLoader
- [original content moved] Lines 326-347

#### Advanced configuration without a full Kedro project
- [original content moved] Lines 349-428

---

### 10. HOW-TO GUIDE: Migrate Config Loaders (`config_loader_migration.md`)

**Status**: Keep as-is ✅

This file is already perfectly structured as a how-to guide and doesn't need reorganization.

---

## Implementation Steps

1. **Create new explanation files:**
   - `configure/configuration_explanation.md`
   - `configure/parameters_and_credentials_explanation.md` (combined)
   - `configure/templating_explanation.md`

2. **Create new how-to guide files:**
   - `configure/how_to_configure_project.md`
   - `configure/how_to_use_parameters.md`
   - `configure/how_to_validate_parameters.md` (separated)
   - `configure/how_to_manage_credentials.md`
   - `configure/how_to_advanced_configuration.md`

3. **Update `mkdocs.yml`** navigation to reflect new structure

4. **Deprecate old files** (or keep as redirects):
   - `configuration_basics.md`
   - `advanced_configuration.md`
   - `parameters.md`
   - `credentials.md`
   - `parameter_validation.md` (now a separate how-to guide)

5. **Update cross-references** in all files to point to new locations

---

## Benefits of This Reorganization

1. **Clear separation of concerns**: Users know where to go for understanding vs. doing
2. **Better learning path**: Users can read explanations first, then follow how-to guides
3. **Easier maintenance**: Each file has a single, clear purpose
4. **Diataxis compliance**: Follows the framework's principles for technical documentation
5. **No content loss**: All existing content is preserved, just reorganized

---

## Notes for Reviewers

- All content marked `[original content moved]` is unchanged from source files
- All content marked `[new content to be reviewed]` is new bridging text to improve flow
- No functional changes to code examples or commands
- All links and cross-references will need updating during implementation
