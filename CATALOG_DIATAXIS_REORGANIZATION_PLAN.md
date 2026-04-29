# Data Catalog Documentation Reorganization Plan (Diataxis Framework)

> **NOTE**: This file will be removed before merge. It exists solely to help reviewers understand the reorganization and track where content has moved from/to.

## Overview
This plan reorganizes the Data Catalog documentation to align with the Diataxis framework by separating **Explanation** (understanding-oriented) content from **How-to Guides** (task-oriented) content, while keeping **Reference** material separate.

**Key Principle**: NO content changes - only moving sections/paragraphs. The documentation below shows what content moves where, so reviewers can easily verify that content has been preserved, not rewritten.

---

## Proposed New Structure

The reorganization creates:
- **3 Explanation files** (understanding-oriented)
- **4 How-to Guide files** (task-oriented)
- **1 Reference file** (information-oriented)

### Navigation Structure (mkdocs.yml)
```yaml
- Data Catalog:
    - Understanding the Data Catalog:
        - Data Catalog concepts: catalog-data/data_catalog_explanation.md
        - Dataset factories concepts: catalog-data/dataset_factories_explanation.md
        - Partitioned and incremental datasets concepts: catalog-data/partitioned_datasets_explanation.md
        - Lazy loading: catalog-data/lazy_loading.md
    - How-to Guides:
        - Configure the Data Catalog: catalog-data/how_to_configure_catalog.md
        - Use dataset factories: catalog-data/how_to_use_dataset_factories.md
        - Use partitioned and incremental datasets: catalog-data/how_to_use_partitioned_datasets.md
        - Access the Data Catalog in code: catalog-data/advanced_data_catalog_usage.md
    - Reference:
        - Data Catalog YAML examples: catalog-data/data_catalog_yaml_examples.md
```

---

## Detailed Content Mapping

### 1. EXPLANATION: Data Catalog Concepts (`data_catalog_explanation.md`)

**Purpose**: Help users understand what the Data Catalog is and how it works

**Content to move from `data_catalog.md`:**

#### Section: What is the Data Catalog
- [original content moved] Lines 1-11:
  - Title
  - Definition of Data Catalog
  - Reference to kedro-datasets package
  - Overview of basic sections

#### Section: The basics of catalog.yml
- [original content moved] Lines 12-31:
  - Basic structure explanation
  - Example of basic catalog configuration

#### Section: Configuring dataset parameters
- [original content moved] Lines 33-70:
  - How dataset configuration is structured
  - Explanation of top-level keys
  - Type, filepath, and other parameters

#### Section: Dataset types
- [original content moved] Lines 72-76:
  - Supported connectors overview
  - Reference to kedro-datasets documentation

#### Section: Dataset filepath and protocols
- [original content moved] Lines 78-94:
  - How fsspec works
  - Supported protocols (local, HDFS, S3, GCS, Azure, HTTP)

#### Section: Understanding load, save, and filesystem arguments
- [original content moved] Lines 100-158:
  - Explanation of load_args, save_args, fs_args
  - How they work with underlying libraries

#### Section: Dataset credentials
- [original content moved] Lines 160-184:
  - How credentials work with the Data Catalog
  - How they are passed to datasets

#### Section: Dataset versioning concepts
- [original content moved] Lines 187-232:
  - What versioning is
  - How versioning works
  - How to check if a dataset supports versioning

#### Section: Using Data Catalog with Kedro configuration
- [original content moved] Lines 234-259:
  - How configuration environments work with the catalog
  - Configuration merging behavior

---

### 2. EXPLANATION: Dataset Factories Concepts (`dataset_factories_explanation.md`)

**Purpose**: Help users understand what dataset factories are and how they work

**Content to move from `kedro_dataset_factories.md`:**

#### Section: What are dataset factories
- [original content moved] Lines 1-45:
  - Introduction to dataset factories
  - Why they exist
  - Basic pattern example
  - How pattern matching works

#### Section: Types of patterns
- [original content moved] Lines 47-92:
  - Dataset patterns
  - User catch-all pattern
  - Default runtime patterns

#### Section: Pattern resolution order
- [original content moved] Lines 94-107:
  - How Kedro resolves patterns
  - Order of precedence

#### Section: How resolution works in practice
- [original content moved] Lines 109-161:
  - Resolution examples
  - Default vs runtime behaviour

#### Section: Implementation details and Python API
- [original content moved] Lines 469-529:
  - CatalogCommandsMixin explanation
  - Why mixin approach
  - How it works

---

### 3. EXPLANATION: Partitioned and Incremental Datasets Concepts (`partitioned_datasets_explanation.md`)

**Purpose**: Help users understand partitioned and incremental datasets

**Content to move from `partitioned_and_incremental_datasets.md`:**

#### Section: What are partitioned datasets
- [original content moved] Lines 1-16:
  - Introduction to partitioned datasets
  - Use cases
  - Features
  - Definition of partition

#### Section: Understanding dataset definition
- [original content moved] Lines 84-99:
  - What dataset definition is
  - Shorthand vs full notation

#### Section: Partitioned dataset credentials
- [original content moved] Lines 100-115:
  - How credentials work with partitioned datasets
  - Different scenarios

#### Section: How partitioned dataset loading works
- [original content moved] Lines 117-162:
  - Lazy loading approach
  - What is returned
  - Partition ID explanation
  - Caching behavior

#### Section: How partitioned dataset saving works
- [original content moved] Lines 164-209:
  - Save operation overview
  - Safety considerations

#### Section: Partitioned dataset lazy saving
- [original content moved] Lines 211-256:
  - What is lazy saving
  - When to use it
  - How to disable it

#### Section: What are incremental datasets
- [original content moved] Lines 258-264:
  - Introduction to IncrementalDataset
  - Checkpoint concept
  - Use case

#### Section: How incremental dataset loading works
- [original content moved] Lines 266-270:
  - Differences from partitioned dataset loading

#### Section: How incremental dataset confirmation works
- [original content moved] Lines 276-329:
  - What confirmation means
  - Important notes about confirmation

#### Section: Understanding checkpoint configuration
- [original content moved] Lines 332-391:
  - How checkpoint config works
  - Special keys

---

### 4. EXPLANATION: Lazy Loading (`lazy_loading.md`)

**Status**: Keep as-is ✅

This file is already a perfect explanation file.

---

### 5. HOW-TO GUIDE: Configure the Data Catalog (`how_to_configure_catalog.md`)

**Purpose**: Step-by-step guides for configuring the Data Catalog in YAML

**Content to move from `data_catalog.md`:**

#### Introduction
- [new content to be reviewed] Brief intro about this guide

#### How to configure basic datasets
- [original content moved] Lines 12-31:
  - Basic catalog.yml structure
  - Example configurations

#### How to configure dataset parameters
- [original content moved] Lines 33-70:
  - Practical configuration examples

#### How to use load, save, and filesystem arguments
- [original content moved] Lines 100-158:
  - Practical examples of load_args, save_args, fs_args

#### How to use credentials
- [original content moved] Lines 160-184:
  - Setting up credentials
  - Referencing credentials in catalog

#### How to enable dataset versioning
- [original content moved] Lines 187-223:
  - Practical versioning setup
  - Using load-versions flag
  - Listing versions

#### How to use catalog with different environments
- [original content moved] Lines 234-259:
  - Setting up base and local catalogs
  - Overriding catalog entries

---

### 6. HOW-TO GUIDE: Use Dataset Factories (`how_to_use_dataset_factories.md`)

**Purpose**: Practical guide to using dataset factories

**Content to move from `kedro_dataset_factories.md`:**

#### Introduction
- [new content to be reviewed] Brief intro about this guide

#### How to generalise datasets of the same type
- [original content moved] Lines 163-231:
  - Practical example combining datasets
  - Updating pipeline references

#### How to generalise datasets using namespaces
- [original content moved] Lines 232-282:
  - Namespace pattern examples
  - Pipeline configuration

#### How to generalise datasets in different layers
- [original content moved] Lines 284-322:
  - Multiple placeholder examples

#### How to use multiple dataset factories
- [original content moved] Lines 324-344:
  - Pattern matching and ranking

#### How to override default dataset creation
- [original content moved] Lines 346-357:
  - Catch-all pattern usage

#### How to use the user-facing API
- [original content moved] Lines 359-372:
  - CatalogConfigResolver methods
  - Pattern matching APIs

#### How to use catalog CLI commands
- [original content moved] Lines 374-468:
  - describe-datasets
  - list-patterns
  - resolve-patterns

#### How to compose catalog with mixins
- [original content moved] Lines 490-529:
  - Practical examples of using mixins

---

### 7. HOW-TO GUIDE: Use Partitioned and Incremental Datasets (`how_to_use_partitioned_datasets.md`)

**Purpose**: Practical guide to using partitioned and incremental datasets

**Content to move from `partitioned_and_incremental_datasets.md`:**

#### Introduction
- [new content to be reviewed] Brief intro about this guide

#### How to use PartitionedDataset
- [original content moved] Lines 17-83:
  - YAML configuration
  - Programmatic instantiation
  - Full configuration example
  - Arguments table

#### How to load partitioned datasets
- [original content moved] Lines 117-162:
  - Node function example
  - Practical usage

#### How to save partitioned datasets
- [original content moved] Lines 164-209:
  - Save configuration
  - Node example
  - Safety notes

#### How to use lazy saving
- [original content moved] Lines 211-256:
  - Callable examples
  - Disabling lazy saving

#### How to use IncrementalDataset
- [original content moved] Lines 258-275:
  - Basic setup
  - Loading

#### How to confirm incremental datasets
- [original content moved] Lines 276-329:
  - Confirmation in nodes
  - Deferred confirmation examples

#### How to configure checkpoint
- [original content moved] Lines 332-391:
  - Checkpoint config examples
  - Special keys usage

---

### 8. HOW-TO GUIDE: Access the Data Catalog in Code (`advanced_data_catalog_usage.md`)

**Status**: Keep as-is ✅

This file is already structured as a how-to guide and doesn't need reorganization.

---

### 9. REFERENCE: Data Catalog YAML Examples (`data_catalog_yaml_examples.md`)

**Status**: Keep as-is ✅

This file is pure reference material - examples for different scenarios.

---

### 10. Overview Page (`introduction.md`)

**Status**: Update to reference new structure ✅

Update the overview page to point to the new organization.

---

## Implementation Steps

1. **Create new explanation files:**
   - `catalog-data/data_catalog_explanation.md`
   - `catalog-data/dataset_factories_explanation.md`
   - `catalog-data/partitioned_datasets_explanation.md`
   - Keep `catalog-data/lazy_loading.md` as-is

2. **Create new how-to guide files:**
   - `catalog-data/how_to_configure_catalog.md`
   - `catalog-data/how_to_use_dataset_factories.md`
   - `catalog-data/how_to_use_partitioned_datasets.md`
   - Keep `catalog-data/advanced_data_catalog_usage.md` as-is

3. **Keep reference file as-is:**
   - `catalog-data/data_catalog_yaml_examples.md`

4. **Update `mkdocs.yml`** navigation to reflect new structure

5. **Deprecate old files** (or keep as redirects):
   - `data_catalog.md`
   - `kedro_dataset_factories.md`
   - `partitioned_and_incremental_datasets.md`

6. **Update cross-references** in all files to point to new locations

7. **Update overview page** `introduction.md` to reference new structure

---

## Benefits of This Reorganization

1. **Clear separation of concerns**: Users know where to go for understanding vs. doing
2. **Better learning path**: Users can read explanations first, then follow how-to guides
3. **Easier maintenance**: Each file has a single, clear purpose
4. **Diataxis compliance**: Follows the framework's principles for technical documentation
5. **No content loss**: All existing content is preserved, just reorganized
6. **Right-sized files**: Balanced content distribution across explanation and how-to files

---

## Notes for Reviewers

- All content marked `[original content moved]` is unchanged from source files
- All content marked `[new content to be reviewed]` is new bridging text to improve flow
- No functional changes to code examples or commands
- All links and cross-references will need updating during implementation
