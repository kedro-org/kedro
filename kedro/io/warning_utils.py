import threading
from types import TracebackType

# Thread-local flag to support safe concurrent use
_catalog_internal_context: threading.local = threading.local()
_catalog_internal_context.suppress_warning = False  # type: ignore[attr-defined]


class suppress_catalog_warning:
    def __enter__(self) -> None:
        _catalog_internal_context.suppress_warning = True  # type: ignore[attr-defined]

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _catalog_internal_context.suppress_warning = False  # type: ignore[attr-defined]


def is_warning_suppressed() -> bool:
    return getattr(_catalog_internal_context, "suppress_warning", False)
