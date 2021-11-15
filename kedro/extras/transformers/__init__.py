"""``kedro.extras.transformers`` is the home of Kedro's dataset transformers."""
import warnings

from .memory_profiler import ProfileMemoryTransformer
from .time_profiler import ProfileTimeTransformer

__all__ = ["ProfileMemoryTransformer", "ProfileTimeTransformer"]

warnings.simplefilter("default", DeprecationWarning)

warnings.warn(
    "Support for transformers will be deprecated in Kedro 0.18.0. "
    "Please use Hooks `before_dataset_loaded`/`after_dataset_loaded` or "
    "`before_dataset_saved`/`after_dataset_saved` instead.",
    DeprecationWarning,
)
