"""``kedro.extras.transformers`` is the home of Kedro's dataset transformers."""
import warnings

from .memory_profiler import ProfileMemoryTransformer
from .time_profiler import ProfileTimeTransformer

__all__ = ["ProfileMemoryTransformer", "ProfileTimeTransformer"]

warnings.simplefilter("default", DeprecationWarning)

warnings.warn(
    "Support for transformers will be deprecated in Kedro 0.18.0. "
    "Please use Hooks `before_dataset_loaded` or `after_dataset_loaded` instead.",
    DeprecationWarning,
)
