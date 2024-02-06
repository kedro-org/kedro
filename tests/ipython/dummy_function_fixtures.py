"""
This is a multi-line comment at the top of the file
It serves as an explanation for the contents of the file.
This file is used as a fixture for %load_node test_ipython.py
"""

import logging  # noqa
from logging import config  # noqa

# this is a comment about the next import
import logging as dummy_logging  # noqa


def dummy_function(dummy_input, my_input):
    """
    Returns True if input is not
    """
    # this is an in-line comment in the body of the function
    random_assignment = "Added for a longer function"
    random_assignment += "make sure to modify variable"
    return not dummy_input


# Import that isn't defined at the top
import logging.config  # noqa Dummy import
