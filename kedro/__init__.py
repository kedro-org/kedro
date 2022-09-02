"""Kedro is a framework that makes it easy to build robust and scalable
data pipelines by providing uniform project templates, data abstraction,
configuration and pipeline assembly.
"""

__version__ = "0.18.2"


import logging
from contextlib import suppress

with suppress(NameError):
    get_ipython()  # Only available in IPython env
    from .extras.extensions.ipython import load_ipython_extension


logging.getLogger(__name__).addHandler(logging.NullHandler())
