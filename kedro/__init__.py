"""Kedro is a framework that makes it easy to build robust and scalable
data pipelines by providing uniform project templates, data abstraction,
configuration and pipeline assembly.
"""

__version__ = "0.18.2"


import logging

try:
    from IPython import get_ipython
    from .extras.extensions.ipython import load_ipython_extension
except ModuleNotFoundError:
    pass  # Skip it when IPython is not instsalled

logging.getLogger(__name__).addHandler(logging.NullHandler())
