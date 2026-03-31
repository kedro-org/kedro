# Reviewer Note: Configuration Documentation Restructure

## Summary

This PR introduces a new organizational structure for Kedro's configuration documentation, separating conceptual explanations from practical how-to guides following the Diátaxis documentation framework.

## Changes

### New Top-Level Navigation Sections

Two new top-level sections have been added to the documentation navigation (at the same level as "Kedro", "Kedro-Viz", and "Kedro-Datasets"):

- **Concepts**: Explanatory content covering fundamental understanding
  - Configuration basics
  - Configuration environments
  - Parameters and credentials
  - Templating with OmegaConfigLoader

- **How-to Guides**: Task-oriented procedural content
  - Quick start (5-minute guide using spaceflights project)
  - Configure your project
  - Work with parameters
  - Manage credentials
  - Use templating
  - Migrate config loaders

### New Files Created

**Concepts (Explanations):**
- `docs/configure/01_configuration_basics.md`
- `docs/configure/02_configuration_environments.md`
- `docs/configure/03_parameters_and_credentials.md`
- `docs/configure/04_templating_with_omegaconfigloader.md`

**How-to Guides:**
- `docs/configure/quick_start.md`
- `docs/configure/how_to_configure_project.md`
- `docs/configure/how_to_work_with_parameters.md`
- `docs/configure/how_to_manage_credentials.md`
- `docs/configure/how_to_use_templating.md`
- `docs/configure/how_to_migrate_config_loaders.md`

**Reference:**
- `docs/configure/reference.md`

### Existing Files

**Intentionally Unchanged:**
- `docs/configure/configuration_basics.md`
- `docs/configure/parameters.md`
- `docs/configure/credentials.md`
- `docs/configure/advanced_configuration.md`
- `docs/configure/config_loader_migration.md`

These files remain in place to keep this PR focused on introducing the new structure. They can be deprecated or removed in a future PR once the new documentation is validated.

## Design Decisions

1. **Progressive Disclosure**: Advanced content is placed at the end of relevant how-to guides, separated by `---`, rather than in a separate file
2. **Embedded Examples**: Practical examples are embedded directly in guides to minimize navigation
3. **Safe Credentials**: All credential examples use placeholder syntax (`<your_key>`) to pass security scans
4. **Spaceflights-Based**: Quick start guide uses actual content from the spaceflights tutorial project for accuracy

## Future Work

- Deprecate old configuration files once new structure is validated
- Add redirects from old URLs to new URLs
- Extend Concepts/How-to structure to other documentation areas (catalog, pipelines, etc.)

## Navigation Structure

```yaml
nav:
  - Kedro: ...
  - Concepts:
      - Configuration: ...
  - How-to Guides:
      - Configuration: ...
  - Kedro-Viz: ...
  - Kedro-Datasets: ...
```
