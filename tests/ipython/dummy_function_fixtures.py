"""
This file serves as a fixture for the %load_node test_ipython.py in the testing suites.
It contains variations of import statements for testing purposes. The usage of the
`logging` library as a dummy library is intentional, as it is part of the standard
libraries, but it can be replaced with any other library for further testing scenarios.
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


def dummy_function_with_optional_arg(dummy_input, my_input, optional=None):
    """
    Returns True if input is not
    """
    # this is an in-line comment in the body of the function
    random_assignment = "Added for a longer function"
    random_assignment += "make sure to modify variable"
    return not dummy_input


# Import that isn't defined at the top
import logging.config  # noqa Dummy import


def dummy_nested_function(dummy_input):
    def nested_function(input):
        return not input

    return nested_function(dummy_input)


def dummy_function_with_loop(dummy_list):
    for x in dummy_list:
        continue
    return len(dummy_list)
