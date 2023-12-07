from __future__ import annotations

import pickle
from multiprocessing.managers import SyncManager
from typing import Any

from kedro.io.core import AbstractDataset, DatasetError


class SharedMemoryDataset(AbstractDataset):
    """``SharedMemoryDataset`` is a wrapper class for a shared MemoryDataset in SyncManager."""

    def __init__(self, manager: SyncManager = None):
        """Creates a new instance of ``SharedMemoryDataset``,
        and creates shared MemoryDataset attribute.

        Args:
            manager: An instance of multiprocessing manager for shared objects.

        """
        if manager:
            self.shared_memory_dataset = manager.MemoryDataset()  # type: ignore
        else:
            self.shared_memory_dataset = None  # type: ignore

    def set_manager(self, manager: SyncManager):
        self.shared_memory_dataset = manager.MemoryDataset()  # type: ignore

    def __getattr__(self, name):
        # This if condition prevents recursive call when deserialising
        if name == "__setstate__":
            raise AttributeError()
        return getattr(self.shared_memory_dataset, name)  # pragma: no cover

    def _load(self) -> Any:
        return self.shared_memory_dataset.load()

    def _save(self, data: Any):
        """Calls save method of a shared MemoryDataset in SyncManager."""
        try:
            self.shared_memory_dataset.save(data)
        except Exception as exc:
            # Checks if the error is due to serialisation or not
            try:
                pickle.dumps(data)
            except Exception as serialisation_exc:  # SKIP_IF_NO_SPARK
                raise DatasetError(
                    f"{str(data.__class__)} cannot be serialised. ParallelRunner "
                    "implicit memory datasets can only be used with serialisable data"
                ) from serialisation_exc
            raise exc  # pragma: no cover

    def _describe(self) -> dict[str, Any]:
        """SharedMemoryDataset doesn't have any constructor argument to return."""
        return {}
