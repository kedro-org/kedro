<!-- vale Kedro.headings = NO -->

# Templating with OmegaConfigLoader

<!-- vale Kedro.headings = YES -->

## Introduction to templating

Templating, or [variable interpolation](https://omegaconf.readthedocs.io/en/2.3_branch/usage.html#variable-interpolation) as it's called in `OmegaConf`, allows you to reference values from one part of your configuration in another. This helps you avoid duplication and makes your configuration easier to maintain.

When you use templating, you can define a value in one place and reference it multiple times across your configuration files. If you need to change that value, you update it in a single location.

## Why use templating?

A Kedro project typically maintains parameters, catalog entries, and other configuration across several environments — `base`, `local`, and possibly one per deployment target. Without templating, the same value (for example, a dataset type, an S3 bucket name, or a model random seed) often ends up copied and pasted into multiple places. As the project grows, those copies drift out of sync.

Templating in `OmegaConfigLoader` addresses three related problems:

- **Duplication.** Values used in more than one place — dataset types, cloud storage locations, model hyperparameters — live in a single location.
- **Environment differences.** A single templated catalog or parameter file can adapt to different environments by resolving to different values at load time.
- **Runtime overrides.** Values that change per run (for example, a date or an experiment name) can be injected from the CLI without editing configuration files.

## Choosing a templating approach

`OmegaConfigLoader` supports four complementary ways to make configuration dynamic. The right choice depends on where the value comes from and when it changes:

| Situation | Approach | Reference style |
|---|---|---|
| A value is reused within one configuration type (for example, the same dataset type across several catalog entries) | Variable interpolation | `${...}` |
| A value is shared across configuration types, for example between parameters and the catalog | Globals | `${globals:...}` |
| A value that is known when the pipeline runs, for example a date or experiment name passed through the CLI | Runtime parameters | `${runtime_params:...}` |
| A value must be computed dynamically, for example today's date or a non-primitive type | Custom resolvers | `${my_resolver:...}` |

## Variable interpolation

`OmegaConfigLoader` resolves OmegaConf-style variable interpolation when it loads configuration. A placeholder can reference another key in the same file. It can also reference a key in another file loaded under the same config pattern (for example, the patterns for parameters or catalog files).

From Kedro `0.18.10`, interpolation also works in catalog files. Template values there must start with an underscore (`_`) so they are not mistaken for catalog entries.

Reach for variable interpolation when a value is defined alongside the configuration that uses it and does not need to be shared with other configuration types.

For the step-by-step recipes, see [How to template parameters](how_to_use_templating.md#how-to-template-parameters), [How to template catalog files](how_to_use_templating.md#how-to-template-catalog-files), and [How to template other configuration files](how_to_use_templating.md#how-to-template-other-configuration-files).

## Globals

Globals are a named set of values that are visible to every configuration type. They are the right choice when the same value is needed in both parameters and the catalog, for example a shared S3 bucket name.

From Kedro `0.18.13`, global variables live in `globals.yml` files, one per environment. Reference them with the `${globals:...}` resolver.

To change which files count as globals, [overwrite the `globals` key in `config_patterns`](how_to_configure_project.md#how-to-change-which-configuration-files-are-loaded). You can also bypass the configuration loading rules to set them directly on the loader. When the same key exists in both your base and runtime environments, the runtime environment value wins.

For the step-by-step recipe, see [How to use global variables with the `OmegaConfigLoader`](how_to_use_templating.md#how-to-use-global-variables-with-the-omegaconfigloader).

## Runtime parameters

Runtime parameters are values supplied when a pipeline runs. They are passed through the `kedro run --params` CLI option and injected into configuration with the `runtime_params` resolver. They merge into the `KedroContext` alongside parameters from configuration files.

Because they change from run to run, runtime parameters suit values that are known at execution time. Examples are a run date or an experiment name. They cannot override globals, and they cannot be used inside `globals` files, to avoid unintentional overrides.

Take care with configuration entries that control code execution. A catalog entry's `type` selects the dataset class Kedro instantiates. Resolving it from `runtime_params` would let whoever supplies the parameter choose arbitrary classes.

For the step-by-step recipe, see [How to override configuration with runtime parameters with the `OmegaConfigLoader`](how_to_use_templating.md#how-to-override-configuration-with-runtime-parameters-with-the-omegaconfigloader).

## Resolvers

Resolvers compute configuration values dynamically instead of reading them from a file. Kedro supports custom resolvers registered through `CONFIG_LOADER_ARGS` in your project's `settings.py`. It also supports most of OmegaConf's built-in resolvers. `oc.env` is enabled for loading credentials; enabling it for other configuration is discouraged.

Use a custom resolver for values that are unknown until load time. Examples are the current date or a non-primitive type such as a Polars data type.

For the step-by-step recipe, see [How to use resolvers in the `OmegaConfigLoader`](how_to_use_templating.md#how-to-use-resolvers-in-the-omegaconfigloader).
