"""Kedro is a framework that makes it easy to build robust and scalable
data pipelines by providing uniform project templates, data abstraction,
configuration and pipeline assembly.
"""

__version__ = "0.18.2"


import logging

try:
    # Only available in IPython enviornment
    get_ipython()  # pylint: disable
    from .extras.extensions.ipython import load_ipython_extension
except NameError:
    pass

logging.getLogger(__name__).addHandler(logging.NullHandler())
