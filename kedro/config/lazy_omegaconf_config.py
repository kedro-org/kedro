"""Experimental configuration loading with deferred interpolation resolution."""

from __future__ import annotations

import copy
import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from omegaconf import DictConfig, OmegaConf
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import UnsupportedInterpolationType
from omegaconf.resolvers import oc

from kedro.config.abstract_config import AbstractConfigLoader, MissingConfigException
from kedro.config.omegaconf_config import OmegaConfigLoader
from kedro.utils import CLOUD_PROTOCOLS, HTTP_PROTOCOLS, _parse_filepath, experimental

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_RESOLVE_LOCK = threading.Lock()
_UNSET = object()
_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RawConfig:
    base_configs: dict[Path, DictConfig]
    env_configs: dict[Path, DictConfig]
    base_path: str
    env_path: str
    processed_files: set[Path]


@experimental
class LazyOmegaConfigLoader(OmegaConfigLoader):
    """An OmegaConf loader that caches raw config for repeated resolution.

    ``interpolation_scope="environment"`` resolves each environment before merging,
    matching ``OmegaConfigLoader``. ``interpolation_scope="merged"`` merges raw
    environments first and then resolves the result.

        This class intentionally subclasses ``OmegaConfigLoader`` to reuse its raw-file
        loading, validation, resolver and merge helpers while avoiding its eager globals
        resolution and constructor-time resolver registration.

        It currently relies on these inherited private methods:

        - ``_initialise_filesystem_and_protocol`` and ``_register_new_resolvers`` during
            initialisation.
        - ``_read_raw_config`` for environment paths, file discovery, hidden-file handling,
            duplicate checks and credential environment-variable resolution.
        - ``_resolve_from_raw_config`` for the ``"environment"`` interpolation scope.
        - ``_register_globals_resolver`` and ``_register_runtime_params_resolver`` during
            each locked resolution.
        - ``_guard_runtime_params_in_catalog_type`` for catalog type-selection protection.
        - ``_merge_configs`` when a custom merge strategy is configured.

        If this class later moves to ``AbstractConfigLoader``, extract or port those helpers
        and their tests before changing the base class. Update this list when inherited
        private dependencies change.
    """

    def __init__(  # noqa: PLR0913
        self,
        conf_source: str | Path,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
        *,
        config_patterns: dict[str, list[str]] | None = None,
        base_env: str | None = None,
        default_run_env: str | None = None,
        custom_resolvers: dict[str, Callable | tuple[Callable, dict[str, Any]]]
        | None = None,
        merge_strategy: dict[str, str] | None = None,
        ignore_hidden: bool = True,
        restrict_runtime_params_type_selection: bool = False,
        interpolation_scope: str = "merged",
    ):
        if isinstance(conf_source, Path):
            conf_source = str(conf_source)

        if interpolation_scope not in {"environment", "merged"}:
            raise ValueError(
                "interpolation_scope must be either 'environment' or 'merged'."
            )

        self.ignore_hidden = ignore_hidden
        self.restrict_runtime_params_type_selection = (
            restrict_runtime_params_type_selection
        )
        self.base_env = base_env or ""
        self.default_run_env = default_run_env or ""
        self.merge_strategy = merge_strategy or {}
        self.interpolation_scope = interpolation_scope
        self._globals: dict[str, Any] = {}
        self._globals_loaded = False
        self._globals_lock = threading.Lock()
        self._globals_oc: DictConfig | None = None
        self._runtime_params_oc: DictConfig | None = None
        self._runtime_params_hits: set[str] = set()
        self.config_patterns = {
            "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
            "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
            "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
            "globals": ["globals.yml"],
        }
        self.config_patterns.update(config_patterns or {})
        self._custom_resolvers = custom_resolvers
        self._oc_env_custom_resolver = (
            custom_resolvers.get("oc.env") if custom_resolvers else None
        )
        if custom_resolvers:
            custom_resolvers_to_register = {
                name: resolver
                for name, resolver in custom_resolvers.items()
                if name not in {"globals", "runtime_params", "oc.env"}
            }
            if custom_resolvers_to_register:
                self._register_new_resolvers(custom_resolvers_to_register)

        self._fs, self._protocol = self._initialise_filesystem_and_protocol(conf_source)
        if self._protocol in CLOUD_PROTOCOLS or self._protocol in HTTP_PROTOCOLS:
            self._remote_root_path = _parse_filepath(conf_source)["path"].rstrip("/")

        AbstractConfigLoader.__init__(
            self,
            conf_source=conf_source,
            env=env,
            runtime_params=runtime_params,
        )
        self._raw_config_cache: dict[tuple[Any, ...], Any] = {}
        self._raw_config_lock = threading.Lock()
        self._resolved_static_config: dict[str, Any] = {}

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "globals":
            self._globals = value
            self._globals_loaded = True
            self._globals_oc = None
            self._resolved_static_config["globals"] = copy.deepcopy(value)
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> dict[str, Any]:
        if key in self.data:
            return copy.deepcopy(super().__getitem__(key))  # type: ignore[no-any-return]
        if key == "globals":
            self._ensure_globals()
        if key in self._resolved_static_config:
            return copy.deepcopy(self._resolved_static_config[key])
        if key not in self.config_patterns:
            raise KeyError(
                f"No config patterns were found for '{key}' in your config loader"
            )
        self._ensure_globals()
        return self._resolve_config(key)

    def _ensure_globals(self) -> None:
        if self._globals_loaded:
            return
        with self._globals_lock:
            if self._globals_loaded:
                return
            try:
                self._globals = self._resolve_config("globals", runtime_params={})
            except MissingConfigException:
                self._globals = {}
            self._globals_loaded = True
            self._resolved_static_config["globals"] = copy.deepcopy(self._globals)

    def preload(self) -> None:
        """Parse configured files and check duplicates before repeated use.

        This method is optional: ``__getitem__`` loads an uncached key on demand.
        Preloading reads raw files and validates their syntax and duplicate keys. It
        resolves globals and credentials eagerly, but leaves parameters and catalog
        interpolation resolution until those keys are requested.

        Missing environment directories are cached as missing. Accessing a key with no
        matching configuration still raises ``MissingConfigException``.
        """
        self._ensure_globals()
        for key in tuple(self.config_patterns):
            try:
                self._get_raw_config(key)
            except MissingConfigException:
                pass

        if "credentials" in self.config_patterns and "credentials" not in self.data:
            try:
                credentials = self._resolve_config("credentials", runtime_params={})
            except MissingConfigException:
                credentials = {}
            self._resolved_static_config["credentials"] = credentials

    def with_runtime_params(
        self,
        runtime_params: dict[str, Any] | None = None,
        *,
        restrict_runtime_params_type_selection: bool | None = None,
    ) -> LazyOmegaConfigLoader:
        """Return a per-run view sharing this loader's raw configuration snapshot."""
        view = copy.copy(self)
        view.data = self.data.copy()
        view.config_patterns = copy.deepcopy(self.config_patterns)
        view.runtime_params = runtime_params or {}
        view._globals = self._globals
        view._globals_loaded = self._globals_loaded
        view._globals_lock = self._globals_lock
        view._globals_oc = None
        view._runtime_params_oc = None
        view._runtime_params_hits = set()
        view._resolved_static_config = self._resolved_static_config.copy()
        if restrict_runtime_params_type_selection is not None:
            view.restrict_runtime_params_type_selection = (
                restrict_runtime_params_type_selection
            )
        return view

    def _get_unresolved_config(self, key: str) -> DictConfig:
        """Return a read-only raw config merged across the selected environments."""
        if key in self.data:
            config = OmegaConf.create(copy.deepcopy(self.data[key]))
            if not isinstance(config, DictConfig):
                raise TypeError("Config overrides must be mapping values.")
        else:
            config = self._merge_raw_environments(key)
        OmegaConf.set_readonly(config, True)
        return config

    def _get_raw_config(self, key: str) -> _RawConfig:
        patterns = tuple(self.config_patterns.get(key, ()))
        run_env = self.env or self.default_run_env
        cache_key = (key, patterns, self.base_env, run_env)
        with self._raw_config_lock:
            if cache_key not in self._raw_config_cache:
                try:
                    with (
                        _RESOLVE_LOCK,
                        self._oc_env_resolver_scope(allow_builtin=key == "credentials"),
                    ):
                        self._raw_config_cache[cache_key] = _RawConfig(
                            *self._read_raw_config(key)
                        )
                except MissingConfigException as exc:
                    self._raw_config_cache[cache_key] = exc
            raw_config = self._raw_config_cache[cache_key]
        if isinstance(raw_config, MissingConfigException):
            raise MissingConfigException(str(raw_config))
        return raw_config

    def _resolve_config(
        self,
        key: str,
        runtime_params: dict[str, Any] | object = _UNSET,
    ) -> dict[str, Any]:
        raw_config = self._get_raw_config(key)
        params = (
            self.runtime_params
            if runtime_params is _UNSET
            else cast("dict[str, Any] | None", runtime_params)
        )
        previous = (
            self.runtime_params,
            self._runtime_params_oc,
            self._runtime_params_hits,
        )
        with (
            _RESOLVE_LOCK,
            self._oc_env_resolver_scope(allow_builtin=key == "credentials"),
        ):
            self.runtime_params = params or {}
            self._runtime_params_oc = None
            self._runtime_params_hits = set()
            self._register_globals_resolver()
            self._register_runtime_params_resolver()
            try:
                if self.interpolation_scope == "environment":
                    return self._resolve_from_raw_config(
                        key,
                        raw_config.base_configs,
                        raw_config.env_configs,
                        raw_config.base_path,
                        raw_config.env_path,
                        raw_config.processed_files,
                    )
                return self._resolve_merged_config(key, raw_config)
            finally:
                self._register_runtime_params_resolver()
                (
                    self.runtime_params,
                    self._runtime_params_oc,
                    self._runtime_params_hits,
                ) = previous

    @staticmethod
    def _copy_raw_config(raw_config: _RawConfig) -> _RawConfig:
        return _RawConfig(
            base_configs=copy.deepcopy(raw_config.base_configs),
            env_configs=copy.deepcopy(raw_config.env_configs),
            base_path=raw_config.base_path,
            env_path=raw_config.env_path,
            processed_files=set(raw_config.processed_files),
        )

    def _merge_raw_environments(
        self, key: str, raw_config: _RawConfig | None = None
    ) -> DictConfig:
        raw_config = raw_config if raw_config is not None else self._get_raw_config(key)
        copied_config = self._copy_raw_config(raw_config)
        base = self._merge_dict_configs(*copied_config.base_configs.values())
        env = self._merge_dict_configs(*copied_config.env_configs.values())
        if (self.env or self.default_run_env) == self.base_env:
            merged = base
        else:
            strategy = self.merge_strategy.get(key, "destructive").lower()
            if strategy == "destructive":
                base_container = self._to_dict(base)
                env_container = self._to_dict(env)
                common_keys = base_container.keys() & env_container.keys()
                if common_keys:
                    _logger.debug(
                        "Config from path '%s' will override the following "
                        "existing top-level config keys: %s",
                        copied_config.env_path,
                        ", ".join(sorted(common_keys)),
                    )
                base_container.update(env_container)
                merged = OmegaConf.create(base_container)
            elif strategy == "soft":
                merged = self._merge_dict_configs(base, env)
            else:
                base_container = self._to_dict(base)
                env_container = self._to_dict(env)
                merged = OmegaConf.create(
                    self._merge_configs(
                        base_container, env_container, key, copied_config.env_path
                    )
                )
        if not copied_config.processed_files and key != "globals":
            raise MissingConfigException(
                f"No files of YAML or JSON format found in {copied_config.base_path} or {copied_config.env_path} matching"
                f" the glob pattern(s): {[*self.config_patterns[key]]}"
            )
        return merged

    def _resolve_merged_config(
        self, key: str, raw_config: _RawConfig
    ) -> dict[str, Any]:
        merged = self._merge_raw_environments(key, raw_config)
        if key == "parameters":
            merged = self._merge_dict_configs(
                merged, OmegaConf.create(self.runtime_params)
            )

        guard_config = copy.deepcopy(merged) if key == "catalog" else None
        if key == "globals":
            OmegaConf.clear_resolver("runtime_params")
        try:
            resolved_container = OmegaConf.to_container(merged, resolve=True)
        except UnsupportedInterpolationType as exc:
            if key == "globals" and "runtime_params" in str(exc):
                raise UnsupportedInterpolationType(
                    "The `runtime_params:` resolver is not supported for globals."
                ) from exc
            raise

        resolved = cast("dict[str, Any]", resolved_container)
        if key == "catalog":
            self._guard_runtime_params_in_catalog_type([guard_config], resolved)
        elif isinstance(resolved, dict):
            resolved = {k: v for k, v in resolved.items() if not k.startswith("_")}
        return resolved

    @staticmethod
    def _merge_dict_configs(*configs: DictConfig) -> DictConfig:
        merged = OmegaConf.merge(*configs) if configs else OmegaConf.create({})
        return cast("DictConfig", merged)

    @staticmethod
    def _to_dict(config: DictConfig) -> dict[str, Any]:
        container = OmegaConf.to_container(config, resolve=False)
        return cast("dict[str, Any]", container)

    @contextmanager
    def _oc_env_resolver_scope(self, *, allow_builtin: bool = False) -> Iterator[None]:
        """Temporarily register the configured oc.env resolver and restore the prior one."""
        resolver = self._oc_env_custom_resolver
        previous_resolver = OmegaConf._get_resolver("oc.env")
        try:
            if resolver is None and allow_builtin:
                OmegaConf.register_new_resolver("oc.env", oc.env, replace=True)
            elif resolver is None:
                OmegaConf.clear_resolver("oc.env")
            elif isinstance(resolver, tuple):
                resolver_fn, resolver_kwargs = resolver
                kwargs = dict(resolver_kwargs)
                kwargs.pop("replace", None)
                OmegaConf.register_new_resolver(
                    "oc.env", resolver_fn, replace=True, **kwargs
                )
            else:
                OmegaConf.register_new_resolver("oc.env", resolver, replace=True)
            yield
        finally:
            if previous_resolver is None:
                OmegaConf.clear_resolver("oc.env")
            else:
                BaseContainer._resolvers["oc.env"] = previous_resolver
