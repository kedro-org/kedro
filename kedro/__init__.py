"""Kedro is a framework that makes it easy to build robust and scalable
data pipelines by providing uniform project templates, data abstraction,
configuration and pipeline assembly.
"""

import sys
import warnings

__version__ = "0.18.14"


class KedroDeprecationWarning(DeprecationWarning):
    """Custom class for warnings about deprecated Kedro features."""


class KedroPythonVersionWarning(UserWarning):
    """Custom class for warnings about incompatibilities with Python versions."""


if not sys.warnoptions:
    warnings.simplefilter("default", KedroDeprecationWarning)
    warnings.simplefilter("error", KedroPythonVersionWarning)

if sys.version_info >= (3, 12):
    warnings.warn(
        """Kedro is not yet fully compatible with this Python version.
To proceed at your own risk and ignore this warning,
run Kedro with `python -W "default:Kedro is not yet fully compatible" -m kedro ...`
or set the PYTHONWARNINGS environment variable accordingly.""",
        KedroPythonVersionWarning,
    )
