"""Kedro is a framework that makes it easy to build robust and scalable
data pipelines by providing uniform project templates, data abstraction,
configuration and pipeline assembly.
"""

import sys
import warnings

__version__ = "0.18.12"


class KedroPythonVersionWarning(UserWarning):
    """Custom class for warnings about incompatibilities with Python versions."""

    pass


if not sys.warnoptions:
    warnings.simplefilter("error", KedroPythonVersionWarning)

if sys.version_info >= (3, 11):
    warnings.warn(
        """Kedro is not yet fully compatible with this Python version.
To proceed at your own risk and ignore this warning,
run Kedro with `python -W "default:Kedro is not yet fully compatible" -m kedro ...`
or set the PYTHONWARNINGS environment variable accordingly.""",
        KedroPythonVersionWarning,
    )
