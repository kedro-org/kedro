"""``kedro.ipython`` contains an IPython extension.
"""
from contextlib import suppress

with suppress(NameError):
    # Only available in IPython env
    get_ipython()  # NOQA pylint: disable=undefined-variable
    from ..extras.extensions.ipython import (
        load_ipython_extension,  # NOQA pylint: disable=unused-import
    )
