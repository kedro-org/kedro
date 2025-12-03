# Experimental APIs in Kedro

Kedro provides an `@experimental` decorator that allows the core team and plugin authors to introduce new,
early-stage, or unstable APIs without committing to long-term stability.

This mechanism helps Kedro evolve faster while giving users explicit visibility into which parts of the
public API are still undergoing refinement.

## Why experimental APIs?

Experimental features allow us to:

- Introduce new APIs earlier and validate them with real usage.
- Iterate fast without strict backwards-compatibility constraints.
- Make experimental status clear, so users know what to expect.
- Gather usage signals before promoting features to stable APIs.
- Provide a foundation for the hybrid strategy adopted by the Kedro team:

    - **Lightweight** experiments: `@experimental`
    - **Large or dependency-heavy** features: external plugins

## The `@experimental` decorator

Kedro exposes an `@experimental` decorator that can be applied to:

- functions
- classes
- other callables

It marks the object as experimental and triggers a `KedroExperimentalWarning` on first use (function calling or class instantiation).

See the implementation and usage examples in `kedro/experimental.py`.

The decorator **does not**:

- restrict usage
- change runtime behaviour
- introduce additional dependencies

### Disabling experimental warnings

You can suppress `KedroExperimentalWarning` if you choose to adopt a feature without warning noise:

```python
import warnings
from kedro.utils import KedroExperimentalWarning

warnings.filterwarnings("ignore", category=KedroExperimentalWarning)
```

## Migration expectations

Experimental APIs:

- may change signature
- may be replaced
- may be promoted to stable API (and documented officially)
- may be removed based on lack of adoption

These changes will be communicated during minor version releases, and migration guides will be provided for any major revisions.
