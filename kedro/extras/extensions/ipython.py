"""
This file and directory exists purely for backwards compatibility of the following:
%load_ext kedro.extras.extensions.ipython
from kedro.extras.extensions.ipython import reload_kedro

Any modifications to the IPython extension should now be made in kedro/ipython/.
The Kedro IPython extension should always be loaded as %load_ext kedro.ipython.
Line magics such as reload_kedro should always be called as line magics rather than
importing the underlying Python functions.
"""
import warnings

from kedro import KedroDeprecationWarning
from kedro.ipython import (  # noqa  # noqa: unused-import
    load_ipython_extension,
    reload_kedro,
)

warnings.warn(
    "kedro.extras.extensions.ipython should be accessed only using the alias "
    "kedro.ipython. The unaliased name will be removed in Kedro 0.19.0.",
    KedroDeprecationWarning,
)
