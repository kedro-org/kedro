import threading

# Thread-local flag to support safe concurrent use
_catalog_internal_context = threading.local()
_catalog_internal_context.suppress_warning = False


class suppress_catalog_warning:
    def __enter__(self):
        _catalog_internal_context.suppress_warning = True

    def __exit__(self, exc_type, exc_value, traceback):
        _catalog_internal_context.suppress_warning = False


def is_warning_suppressed():
    return getattr(_catalog_internal_context, "suppress_warning", False)
