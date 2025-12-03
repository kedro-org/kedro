# Experimental APIs in Kedro

Kedro provides an `@experimental` decorator that allows the core team and plugin authors to introduce new,
early-stage, or unstable APIs without committing to long-term stability immediately.

This mechanism helps Kedro evolve faster while giving users explicit visibility into which parts of the
public API are still undergoing refinement.

## Why experimental APIs?

Experimental features allow us to:

- Introduce new APIs earlier and validate them with real usage.
- Iterate quickly without strict backwards-compatibility constraints.
- Make experimental status obvious, so users know what to expect.
- Gather usage signals before promoting features to stable APIs.
- Provide a foundation for the hybrid strategy adopted by the Kedro team:

    - **Lightweight** experiments: via `@experimental`
    - **Large or dependency-heavy** features: via external plugins

## The `@experimental` decorator

Kedro exposes an `@experimental` decorator that can be applied to:

- functions
- classes
- other callables

It marks the object as experimental and triggers a `KedroExperimentalWarning` on first use (function calling or class instantiation).

See the implementation and usage examples in `kedro/experimental.py`.

The decorator **does not**:

- restrict usage
- modify runtime behaviour
- introduce additional dependencies

### When to use @experimental

Use the decorator when adding:

- Small additions to core Kedro
- Features likely to stabilise soon
- APIs requiring user feedback

### When NOT to use it

Use a plugin instead of the decorator when:

- the feature requires heavy external dependencies (ML, AI, visualisation libraries)
- the experimentation affects installation size or startup performance
- the feature is large enough to evolve independently

## Migration expectations

Experimental APIs:

- may change signature
- may be replaced
- may be promoted to stable API (and documented officially)
- may be removed based on lack of adoption

These changes will be communicated during minor version releases, and migration guides will accompany any major revisions.
