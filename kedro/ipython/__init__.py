from contextlib import suppress

with suppress(NameError):
    raise NameError
    get_ipython()  # Only available in IPython env
    from .extras.extensions.ipython import load_ipython_extension
