"""Serving-mode config loader.

Prototype for the structural split described in the discussion of
``KedroServiceSession`` thread safety:

* One ``OmegaConfigLoader`` is created on the session thread at preload time
  and never handed to request threads directly.
* A ``_ConfigSnapshot`` caches the runtime_params-independent output
  (credentials, globals) and the raw parsed per-file configs for
  ``parameters`` and ``catalog``, so no request thread re-reads YAML or
  re-parses ``conf/``.
* Each request builds a cheap ``_ServingConfigLoader`` bound to that
  request's ``runtime_params``. Reads of credentials / globals are lock-free.
  ``parameters`` and ``catalog`` still go through OmegaConf's process-global
  resolver registry, so those calls are serialised by a snapshot-scoped
  ``RLock``. The critical section is small: only the merge + resolve step
  (no file I/O, no YAML parsing), which is exactly what needs to see the
  request's ``runtime_params``.
* The existing ``_guard_runtime_params_in_catalog_type`` security check is
  preserved unchanged -- it runs inside the lock on ``_runtime_params_hits``
  that was reset for this request.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from kedro.config.abstract_config import AbstractConfigLoader, MissingConfigException

if TYPE_CHECKING:
    from pathlib import Path

    from omegaconf import DictConfig

    from kedro.config.omegaconf_config import OmegaConfigLoader


@dataclass
class _RawConfigCache:
    """Raw per-file configs for one key, cached at preload time."""

    base: dict[Path, DictConfig]
    env: dict[Path, DictConfig]
    base_path: str
    env_path: str
    processed_files: set[Path]


@dataclass
class _ConfigSnapshot:
    """Immutable session-scoped config snapshot built once on the session thread.

    Attributes only mutated before request threads start. The ``lock`` guards
    the small resolve step on ``persistent_loader`` (see module docstring).
    """

    persistent_loader: OmegaConfigLoader
    credentials: dict[str, Any]
    globals: dict[str, Any]
    raw_parameters: _RawConfigCache | None
    raw_catalog: _RawConfigCache | None
    lock: threading.RLock = field(default_factory=threading.RLock)


def build_snapshot(persistent_loader: OmegaConfigLoader) -> _ConfigSnapshot:
    """Preload runtime_params-independent config and raw YAML into a snapshot.

    Called once from the session thread before any request threads are started.
    """
    try:
        credentials = deepcopy(persistent_loader["credentials"])
    except MissingConfigException:
        credentials = {}

    globals_ = deepcopy(persistent_loader._globals)

    raw_parameters = _read_raw_cache(persistent_loader, "parameters")
    raw_catalog = _read_raw_cache(persistent_loader, "catalog")

    return _ConfigSnapshot(
        persistent_loader=persistent_loader,
        credentials=credentials,
        globals=globals_,
        raw_parameters=raw_parameters,
        raw_catalog=raw_catalog,
    )


def _read_raw_cache(
    loader: OmegaConfigLoader, key: str
) -> _RawConfigCache | None:
    """Read raw per-file configs for ``key`` once, or return None if absent."""
    try:
        base, env, base_path, env_path, processed = loader._read_raw_configs_for_key(
            key
        )
    except MissingConfigException:
        return None
    return _RawConfigCache(
        base=base,
        env=env,
        base_path=base_path,
        env_path=env_path,
        processed_files=processed,
    )


class _ServingConfigLoader(AbstractConfigLoader):
    """Per-request config loader for serving mode.

    Cheap to construct: holds references to a shared snapshot and this
    request's ``runtime_params``. Credentials / globals are lock-free reads.
    Parameters / catalog delegate to the snapshot's persistent loader under
    the snapshot lock, with the persistent loader's ``runtime_params`` state
    swapped for the duration of the resolve.
    """

    def __init__(
        self,
        snapshot: _ConfigSnapshot,
        runtime_params: dict[str, Any] | None,
        conf_source: str,
        env: str | None,
    ):
        super().__init__(
            conf_source=conf_source, env=env, runtime_params=runtime_params
        )
        self._snapshot = snapshot

    @property
    def restrict_runtime_params_type_selection(self) -> bool:
        """Mirror the persistent loader's setting so callers introspecting the
        loader (e.g. tests, hooks) see the same value they'd see in CLI mode."""
        return self._snapshot.persistent_loader.restrict_runtime_params_type_selection

    def __getitem__(self, key: str) -> Any:
        if key in self:
            return super().__getitem__(key)
        if key == "credentials":
            return deepcopy(self._snapshot.credentials)
        if key == "globals":
            return deepcopy(self._snapshot.globals)
        if key == "parameters":
            return self._resolve_cached(key, self._snapshot.raw_parameters)
        if key == "catalog":
            return self._resolve_cached(key, self._snapshot.raw_catalog)
        # Fall back to the persistent loader (still under lock) for
        # user-defined config_patterns not covered above.
        return self._resolve_uncached(key)

    def _resolve_cached(
        self, key: str, cache: _RawConfigCache | None
    ) -> dict[str, Any]:
        if cache is None:
            raise MissingConfigException(
                f"'{key}' was not available at snapshot build time."
            )
        loader = self._snapshot.persistent_loader
        with self._snapshot.lock:
            with _swapped_runtime_params(loader, self.runtime_params):
                return loader._resolve_from_raw(
                    key,
                    cache.base,
                    cache.env,
                    cache.base_path,
                    cache.env_path,
                    cache.processed_files,
                )

    def _resolve_uncached(self, key: str) -> Any:
        loader = self._snapshot.persistent_loader
        with self._snapshot.lock:
            with _swapped_runtime_params(loader, self.runtime_params):
                # Force a fresh read; persistent loader's UserDict may have
                # cached a prior request's result for this key.
                loader.data.pop(key, None)
                return loader[key]


class _swapped_runtime_params:
    """Context manager: swap the persistent loader's runtime_params state for
    the duration of one resolve, then restore. Must be used under the
    snapshot lock -- resets ``_runtime_params_hits``, which the catalog
    security guard reads."""

    def __init__(
        self, loader: OmegaConfigLoader, runtime_params: dict[str, Any] | None
    ):
        self._loader = loader
        self._runtime_params = runtime_params or {}
        self._saved: tuple[Any, Any, set[str]] | None = None

    def __enter__(self) -> None:
        loader = self._loader
        self._saved = (
            loader.runtime_params,
            loader._runtime_params_oc,
            loader._runtime_params_hits,
        )
        loader.runtime_params = self._runtime_params
        loader._runtime_params_oc = None
        loader._runtime_params_hits = set()

    def __exit__(self, *exc: Any) -> None:
        assert self._saved is not None
        loader = self._loader
        (
            loader.runtime_params,
            loader._runtime_params_oc,
            loader._runtime_params_hits,
        ) = self._saved
