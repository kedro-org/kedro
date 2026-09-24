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

    _RawConfig = tuple[
        dict[Path, DictConfig], dict[Path, DictConfig], str, str, set[Path]
    ]


@dataclass
class _ConfigCache:
    """Session-scoped config cache, built once before request threads start."""

    persistent_loader: OmegaConfigLoader
    credentials: dict[str, Any]
    globals: dict[str, Any]
    raw_by_key: dict[str, _RawConfig | None]
    lock: threading.Lock = field(default_factory=threading.Lock)


def build_config_cache(persistent_loader: OmegaConfigLoader) -> _ConfigCache:
    """Preload runtime_params-independent config and raw YAML into a cache."""
    try:
        credentials = deepcopy(persistent_loader["credentials"])
    except MissingConfigException:
        credentials = {}

    # Constructing `persistent_loader` resolves "globals", which deactivates
    # the `runtime_params:` resolver globally. Re-register it here: request
    # resolves call `_resolve_from_raw_config` directly and never do so.
    persistent_loader._register_runtime_params_resolver()

    raw_by_key: dict[str, _RawConfig | None] = {}
    for key in persistent_loader.config_patterns:
        if key in ("credentials", "globals"):
            continue
        try:
            raw_by_key[key] = persistent_loader._read_raw_config(key)
        except MissingConfigException:
            raw_by_key[key] = None

    return _ConfigCache(
        persistent_loader=persistent_loader,
        credentials=credentials,
        globals=deepcopy(persistent_loader._globals),
        raw_by_key=raw_by_key,
    )


class _ServingConfigLoader(AbstractConfigLoader):
    """Per-request config loader for serving mode, backed by a shared ``_ConfigCache``."""

    def __init__(self, cache: _ConfigCache, runtime_params: dict[str, Any] | None):
        persistent_loader = cache.persistent_loader
        super().__init__(
            conf_source=persistent_loader.conf_source,
            env=persistent_loader.env,
            runtime_params=runtime_params,
        )
        self._cache = cache

    @property
    def restrict_runtime_params_type_selection(self) -> bool:
        """Mirror the persistent loader's setting so callers introspecting the
        loader (e.g. tests, hooks) see the same value they'd see in CLI mode."""
        return self._cache.persistent_loader.restrict_runtime_params_type_selection

    def __getitem__(self, key: str) -> Any:
        if key in self:
            return super().__getitem__(key)
        if key == "credentials":
            return deepcopy(self._cache.credentials)
        if key == "globals":
            return deepcopy(self._cache.globals)
        if key not in self._cache.raw_by_key:
            raise KeyError(
                f"No config patterns were found for '{key}' in your config loader"
            )
        raw = self._cache.raw_by_key[key]
        if raw is None:
            raise MissingConfigException(
                f"'{key}' was not available at cache build time."
            )
        loader = self._cache.persistent_loader
        with self._cache.lock, _swapped_runtime_params(loader, self.runtime_params):
            return loader._resolve_from_raw_config(key, *raw)


class _swapped_runtime_params:
    """Context manager: swap the persistent loader's runtime_params state for
    the duration of one resolve, then restore. Must be used under the
    cache lock -- resets ``_runtime_params_hits``, which the catalog
    security guard reads."""

    def __init__(
        self, loader: OmegaConfigLoader, runtime_params: dict[str, Any] | None
    ):
        self._loader = loader
        self._runtime_params = runtime_params or {}
        self._saved: tuple[Any, Any, set[str]] = (None, None, set())

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
        loader = self._loader
        (
            loader.runtime_params,
            loader._runtime_params_oc,
            loader._runtime_params_hits,
        ) = self._saved
