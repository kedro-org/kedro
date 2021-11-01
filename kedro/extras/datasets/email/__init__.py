"""``AbstractDataSet`` implementations for managing email messages."""

__all__ = ["EmailMessageDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .message_dataset import EmailMessageDataSet
