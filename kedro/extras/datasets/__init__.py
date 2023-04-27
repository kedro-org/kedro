"""``kedro.extras.datasets`` is where you can find all of Kedro's data connectors.
These data connectors are implementations of the ``AbstractDataSet``.
"""

from warnings import warn as _warn

_warn(
    "`kedro.extras.datasets` is deprecated and will be removed in Kedro 0.19, "
    "install `kedro-datasets` instead by running `pip install kedro-datasets`.",
    DeprecationWarning,
    stacklevel=2,
)
