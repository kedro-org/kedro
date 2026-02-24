import logging
import traceback
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any

from kedro.framework import project as kedro_project
from kedro.framework.project import settings
from kedro.framework.session.store import BaseSessionStore
from kedro.utils import find_kedro_project


class AbstractSession(ABC):
    """Abstract base class for Kedro sessions."""

    def __init__(
        self,
        session_id: str,
        package_name: str | None = None,
        project_path: Path | str | None = None,
        save_on_close: bool = False,
        conf_source: str | None = None,
    ):
        self._project_path = Path(
            project_path or find_kedro_project(Path.cwd()) or Path.cwd()
        ).resolve()
        self.session_id = session_id
        self.save_on_close = save_on_close
        self._package_name = package_name or kedro_project.PACKAGE_NAME
        self._store = self._init_store()
        # self._conf_source = conf_source or str(
        #     self._project_path / settings.CONF_SOURCE
        # )

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, tb_: Any) -> None:
        if exc_type:
            self._log_exception(exc_type, exc_value, tb_)
        self.close()

    def _init_store(self) -> BaseSessionStore:
        store_class = settings.SESSION_STORE_CLASS
        classpath = f"{store_class.__module__}.{store_class.__qualname__}"
        store_args = deepcopy(settings.SESSION_STORE_ARGS)
        store_args.setdefault("path", (self._project_path / "sessions").as_posix())
        store_args["session_id"] = self.session_id

        try:
            return store_class(**store_args)  # type: ignore[no-any-return]
        except TypeError as err:
            raise ValueError(
                f"\n{err}.\nStore config must only contain arguments valid "
                f"for the constructor of '{classpath}'."
            ) from err
        except Exception as err:
            raise ValueError(
                f"\n{err}.\nFailed to instantiate session store of type '{classpath}'."
            ) from err

    def _log_exception(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        type_ = [] if exc_type.__module__ == "builtins" else [exc_type.__module__]
        type_.append(exc_type.__qualname__)

        exc_data = {
            "type": ".".join(type_),
            "value": str(exc_value),
            "traceback": traceback.format_tb(exc_tb),
        }
        self._store["exception"] = exc_data

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @property
    def store(self) -> dict[str, Any]:
        """Return a copy of internal store."""
        return dict(self._store)

    @abstractmethod
    def load_context(self) -> dict[str, Any]:
        """Load the session context."""
        pass

    def close(self) -> None:
        """Close the current session and save its store to disk
        if `save_on_close` attribute is True.
        """
        if self.save_on_close:
            self._store.save()

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> None:
        """Run the session."""
        pass

    @abstractmethod
    def create(self, *args: Any, **kwargs: Any) -> "AbstractSession":
        """Create a new session."""
        pass
