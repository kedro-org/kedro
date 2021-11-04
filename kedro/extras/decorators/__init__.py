"""``kedro.extras.decorators`` provides Node/Pipeline Decorators."""
import warnings

warnings.simplefilter("default", DeprecationWarning)

warnings.warn(
    "Support for decorators will be deprecated in Kedro 0.18.0. "
    "Please use Hooks to extend the behaviour of a node or pipeline.",
    DeprecationWarning,
)
