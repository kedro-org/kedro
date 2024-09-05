# ruff: noqa
# multi-lines import
from logging import (
    INFO,
    DEBUG,
    WARN,
    ERROR,
)


def dummy_multiline_import_function(dummy_input, my_input):
    """
    Returns True if input is not
    """
    # this is an in-line comment in the body of the function
    random_assignment = "Added for a longer function"
    random_assignment += "make sure to modify variable"
    return not dummy_input
