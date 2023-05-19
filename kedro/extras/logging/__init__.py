"""
This module contains a logging handler class which produces coloured logs.
"""
import warnings

from .color_logger import ColorHandler
from .rich_logger import RichHandler

__all__ = ["ColorHandler", "Richhandler"]

warnings.simplefilter("default", DeprecationWarning)

warnings.warn(
    "Support for ColorHandler will be removed in Kedro 0.19.0.",
    DeprecationWarning,
)
