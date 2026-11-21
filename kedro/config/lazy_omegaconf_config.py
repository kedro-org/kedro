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
from omegaconf.errors import InterpolationResolutionError, UnsupportedInterpolationType
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
    """Store per-file environment configs and their source paths."""

    base_configs: dict[Path, DictConfig]
    env_configs: dict[Path, DictConfig]
    base_path: str
    env_path: str
    processed_files: set[Path]


@experimental
class LazyOmegaConfigLoader(OmegaConfigLoader):
    """Cache configuration files for deferred, repeated interpolation resolution.

    Read files on first key access and reuse their contents until ``preload()``
    refreshes the cache. Create per-run views with ``with_runtime_params()``.
    Each view uses its own runtime parameters.

    This loader uses these terms:

    - **Raw configuration** consists of parsed ``DictConfig`` objects, one per
      file, grouped by environment and not yet merged. Interpolations in
      credential files are resolved during file loading.
    - **Unresolved configuration** is a ``DictConfig`` that combines files and
      environments without resolving remaining interpolations.
      ``get_unresolved_config()`` returns an explicitly assigned override instead
      when one exists for the key.

    ``interpolation_scope="environment"`` resolves each environment before merging,
    matching ``OmegaConfigLoader``. ``interpolation_scope="merged"`` merges first,
    then resolves. It can add preload overhead but reduce repeated merge work.

    This class subclasses ``OmegaConfigLoader`` to reuse its loading, validation,
    resolver, and merge helpers. Globals loading and resolution are deferred until
    first configuration access or ``preload()``. The globals and runtime-parameter
    resolvers are registered during locked resolution rather than construction.
    Construction leaves any existing registrations of these resolvers unchanged.

    It currently relies on these inherited private methods:

    - ``_initialise_filesystem_and_protocol`` and ``_register_new_resolvers`` during
      initialisation.
    - ``_read_raw_config`` for environment paths, file discovery, hidden-file handling,
      duplicate checks, and credential environment-variable resolution.
    - ``_resolve_from_raw_config`` for the ``"environment"`` interpolation scope.
    - ``_register_globals_resolver`` and ``_register_runtime_params_resolver`` during
      each locked resolution.
    - ``_guard_runtime_params_in_catalog_type`` for catalog type-selection protection.
    - ``_merge_configs`` when a custom merge strategy is configured.

    If this class moves to ``AbstractConfigLoader``, extract or port those helpers
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
        interpolation_scope: str = "environment",
    ):
        """Initialise a ``LazyOmegaConfigLoader`` without reading configuration files.

        Args:
            conf_source: Root directory or remote URL containing configuration files.
            env: Run environment that takes precedence over the base environment.
                Defaults to ``default_run_env`` when omitted.
            runtime_params: Parameters merged into ``parameters`` and available to
                the ``runtime_params`` resolver. Defaults to an empty dictionary.
            config_patterns: Glob patterns for each configuration key. Supplied
                entries override the default catalog, parameters, credentials,
                and globals patterns.
            base_env: Base environment directory. Defaults to the configuration
                root when omitted. Kedro projects normally configure ``"base"``.
            default_run_env: Run environment used when ``env`` is omitted.
                Defaults to the configuration root. Kedro projects normally
                configure ``"local"``.
            custom_resolvers: Resolver names mapped to callables or
                ``(callable, kwargs)`` tuples. Except for reserved resolvers,
                these are registered process-wide during construction, outside
                the resolution lock. A resolver whose name is already registered
                is skipped unless ``replace=True``. Replacing it can affect
                other loaders, even if they were created before runs started.
                Strongly avoid registering or replacing global resolvers during
                runs, including through OmegaConf in Hooks or nodes; doing so
                can interfere with an ongoing resolution. The ``oc.env``
                resolver is scoped to loading and resolution; globals and
                runtime parameters use the loader's own resolvers.
            merge_strategy: Per-key merge strategies: ``"soft"`` or
                ``"destructive"``. Defaults to ``"destructive"``.
            ignore_hidden: Ignore hidden files and directories. Defaults to True.
            restrict_runtime_params_type_selection: Reject catalog dataset types
                resolved through ``runtime_params``. Defaults to False.
                Set to True for runtime parameters from untrusted callers.
            interpolation_scope: ``"environment"`` resolves each environment before
                merging, matching ``OmegaConfigLoader``. ``"merged"`` merges raw
                environments before resolving. Defaults to ``"environment"``.

        Raises:
            ValueError: If ``interpolation_scope`` is not ``"environment"`` or
                ``"merged"``.
        """
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
        self._globals_patterns = list(self.config_patterns["globals"])
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
        self._raw_config_cache: dict[
            tuple[Any, ...], _RawConfig | MissingConfigException
        ] = {}
        self._raw_config_lock = threading.Lock()
        self._merged_config_cache: dict[tuple[Any, ...], DictConfig] = {}
        self._merged_config_lock = threading.Lock()
        self._resolved_static_config: dict[str, Any] = {}

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an explicit override and update cached globals when applicable."""
        if key == "globals":
            self._globals = value
            self._globals_loaded = True
            self._globals_oc = None
            self._resolved_static_config["globals"] = copy.deepcopy(value)
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> dict[str, Any]:
        """Return a resolved copy, caching file reads on first access.

        Explicit overrides and cached globals or preloaded credentials take
        precedence over deferred resolution.

        Raises:
            KeyError: If no configuration patterns exist for the key.
            MissingConfigException: If required directories or matching files
                are missing.
        """
        if key in self.data:
            # The inherited lookup replaces the global runtime resolver. Locking it
            # would deadlock when an override is read from within locked resolution.
            return copy.deepcopy(self.data[key])  # type: ignore[no-any-return]
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
        """Resolve and cache globals on first demand, using no runtime parameters."""
        if self._globals_loaded:
            return
        with self._globals_lock:
            if self._globals_loaded:
                return
            try:
                loader = self
                if "globals" not in self.config_patterns:
                    # ``OmegaConfigLoader`` loads globals in its constructor, so replacing
                    # ``config_patterns`` afterwards must not drop them.
                    loader = copy.copy(self)
                    loader.config_patterns = {
                        **self.config_patterns,
                        "globals": self._globals_patterns,
                    }
                self._globals = loader._resolve_config("globals", runtime_params={})
            except MissingConfigException:
                self._globals = {}
            self._globals_loaded = True
            self._resolved_static_config["globals"] = copy.deepcopy(self._globals)

    def preload(self) -> None:
        """Read and validate configured files, then cache them.

        Every ``preload()`` call re-reads the files and replaces the previous
        cache. Call it again to pick up changes on disk. Key access
        reuses cached files.

        Preloading validates syntax and duplicate keys. It eagerly merges and
        resolves globals and credentials unless explicitly overridden.
        For other keys, it merges environments only with the ``"merged"`` scope.
        The default ``"environment"`` scope defers those merges until key access.
        Interpolation resolution for parameters and catalog remains deferred
        until those keys are requested.

        The cache is replaced only if loading succeeds; on error the previous one
        is kept. Views from ``with_runtime_params()`` keep using the previous cache.
        Explicit values assigned to the loader are kept.

        Missing environment directories are cached as missing. Accessing a key with no
        matching configuration still raises ``MissingConfigException``.

        Raises:
            ParserError: If a configuration file contains invalid YAML or JSON syntax.
            ValueError: If files in the same environment contain duplicate keys,
                or an unsupported merge strategy is used during preloading.
            InterpolationResolutionError: If globals or credentials interpolations
                cannot be resolved.
        """
        fresh = copy.copy(self)
        if self.data:
            _logger.info(
                "preload() keeps the values explicitly set on the loader for %s; "
                "they override the ones configuration files.",
                ", ".join(f"'{key}'" for key in sorted(self.data)),
            )
        fresh._raw_config_cache = {}
        fresh._merged_config_cache = {}
        fresh._resolved_static_config = {}
        fresh._globals_oc = None
        if "globals" in self.data:
            fresh._resolved_static_config["globals"] = copy.deepcopy(self._globals)
        else:
            fresh._globals = {}
            fresh._globals_loaded = False
        fresh._ensure_globals()
        for key in tuple(fresh.config_patterns):
            try:
                raw_config = fresh._get_raw_config(key)
                if fresh.interpolation_scope == "merged":
                    fresh._get_merged_config(key, raw_config)
            except MissingConfigException:
                pass

        if "credentials" in fresh.config_patterns and "credentials" not in self.data:
            try:
                credentials = fresh._resolve_config("credentials", runtime_params={})
            except MissingConfigException:
                credentials = {}
            fresh._resolved_static_config["credentials"] = credentials

        with (
            self._globals_lock,
            self._raw_config_lock,
            self._merged_config_lock,
        ):
            self._raw_config_cache = fresh._raw_config_cache
            self._merged_config_cache = fresh._merged_config_cache
            self._resolved_static_config = fresh._resolved_static_config
            self._globals = fresh._globals
            self._globals_loaded = fresh._globals_loaded
            self._globals_oc = None

    def with_runtime_params(
        self,
        runtime_params: dict[str, Any] | None = None,
        *,
        restrict_runtime_params_type_selection: bool | None = None,
    ) -> LazyOmegaConfigLoader:
        """Return a shallow copy of this loader with replacement runtime parameters.

        The returned view reuses the cached configuration files but resolves
        interpolations using its own runtime parameters.

        Args:
            runtime_params: Parameters for the view, replacing this loader's
                runtime parameters. Defaults to an empty dictionary.
            restrict_runtime_params_type_selection: When True, reject catalog
                dataset types selected through the ``runtime_params`` resolver.
                None keeps this loader's setting. Callers supplying runtime
                parameters from an untrusted source, such as an HTTP request
                body, must set this to True.

        Returns:
            A loader view with separate runtime-resolution state. Later
            ``preload()`` calls on the original loader do not refresh this view.
        """
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

    def get_unresolved_config(self, key: str) -> DictConfig:
        """Return a read-only copy of configuration without resolving interpolations.

        Merge the selected environments, or copy an explicit override.
        Do not apply runtime parameters. Under ``"environment"`` scope, resolving
        this merged copy can differ from normal key access.
        Interpolations in credential files are resolved during file loading.

        Use this method for inspection only, not direct resolution.
        Inspect with ``OmegaConf.to_container(config, resolve=False)``.
        For resolved configuration, use ``loader[key]`` instead.
        Read-only prevents modification, not interpolation resolution.
        Resolving this copy, including accessing interpolated values, uses
        process-global resolvers outside the loader's lock and resolver scope.
        If ``oc.env`` is registered globally, this can bypass the loader's
        credentials-only safeguard for the built-in resolver.

        Args:
            key: Configuration key, such as ``"catalog"`` or ``"parameters"``.

        Returns:
            A read-only ``DictConfig`` preserving remaining interpolation expressions.

        Raises:
            KeyError: If no configuration patterns exist for the key.
            MissingConfigException: If required directories or matching files
                are missing.
            TypeError: If an explicit override is not a mapping.
        """
        if key in self.data:
            config = OmegaConf.create(copy.deepcopy(self.data[key]))
            if not isinstance(config, DictConfig):
                raise TypeError("Config overrides must be mapping values.")
        else:
            config = self._get_merged_config(key)
            with _RESOLVE_LOCK:
                config = copy.deepcopy(config)
        OmegaConf.set_readonly(config, True)
        return config

    def _get_merged_config(
        self, key: str, raw_config: _RawConfig | None = None
    ) -> DictConfig:
        """Return the cached, unresolved merge of the selected environments.

        The result is shared: copy it under ``_RESOLVE_LOCK`` before using or changing it.
        """
        raw_config = raw_config if raw_config is not None else self._get_raw_config(key)
        strategy = self.merge_strategy.get(key, "destructive").lower()
        cache_key = (
            key,
            tuple(self.config_patterns.get(key, ())),
            self.base_env,
            self.env or self.default_run_env,
            strategy,
        )
        with self._merged_config_lock:
            if cache_key not in self._merged_config_cache:
                with _RESOLVE_LOCK:
                    self._merged_config_cache[cache_key] = self._merge_raw_environments(
                        key, raw_config
                    )
            return self._merged_config_cache[cache_key]

    def _get_raw_config(self, key: str) -> _RawConfig:
        """Read and cache per-file configs, including missing-directory errors."""
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
        """Resolve cached files under the resolver lock using the selected scope.

        ``_UNSET`` uses this loader's runtime parameters; an explicit argument
        temporarily replaces them. Restore runtime-resolution state afterwards.
        """
        raw_config = self._get_raw_config(key)
        merged_config = (
            self._get_merged_config(key, raw_config)
            if self.interpolation_scope == "merged"
            else None
        )
        with (
            _RESOLVE_LOCK,
            self._oc_env_resolver_scope(allow_builtin=key == "credentials"),
        ):
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
            self.runtime_params = params or {}
            self._runtime_params_oc = None
            self._runtime_params_hits = set()
            self._register_globals_resolver()
            self._register_runtime_params_resolver()
            try:
                try:
                    if merged_config is None:
                        # The inherited resolver merges in place, so it gets a copy.
                        copied_config = self._copy_raw_config(raw_config)
                        return self._resolve_from_raw_config(
                            key,
                            copied_config.base_configs,
                            copied_config.env_configs,
                            copied_config.base_path,
                            copied_config.env_path,
                            copied_config.processed_files,
                        )
                    return self._resolve_merged_config(key, merged_config)
                except InterpolationResolutionError as exc:
                    if "Runtime parameter '" in str(
                        exc
                    ) and "not found and no default value provided" in str(exc):
                        raise InterpolationResolutionError(
                            f"{exc} Supply this value with `with_runtime_params(...)` "
                            "or provide a default in the interpolation."
                        ) from exc
                    raise
            finally:
                self._register_runtime_params_resolver()
                (
                    self.runtime_params,
                    self._runtime_params_oc,
                    self._runtime_params_hits,
                ) = previous

    @staticmethod
    def _copy_raw_config(raw_config: _RawConfig) -> _RawConfig:
        """Copy per-file configs and file tracking to keep the cache unchanged."""
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
        """Merge copies of raw environments without resolving interpolations.

        Apply the configured merge strategy and reject missing files, except
        for globals. Load raw configuration on demand when none is supplied.
        """
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
        self, key: str, merged_config: DictConfig
    ) -> dict[str, Any]:
        """Resolve a merged-config copy with the active loader resolvers.

        Merge runtime parameters into parameters, guard catalog type selection,
        and remove template keys from non-parameter configurations.
        Call while holding ``_RESOLVE_LOCK``.
        """
        if key == "parameters":
            # ``OmegaConf.merge`` copies its first argument, so the shared one is untouched.
            merged = self._merge_dict_configs(
                merged_config, OmegaConf.create(self.runtime_params)
            )
        else:
            merged = copy.deepcopy(merged_config)

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
            self._guard_runtime_params_in_catalog_type([merged], resolved)
        if key == "parameters":
            return resolved
        # Like ``OmegaConfigLoader``: `_`-prefixed keys are templates, not config.
        return {k: v for k, v in resolved.items() if not k.startswith("_")}

    @staticmethod
    def _merge_dict_configs(*configs: DictConfig) -> DictConfig:
        """Merge mappings without changing the inputs, or return an empty config."""
        merged = OmegaConf.merge(*configs) if configs else OmegaConf.create({})
        return cast("DictConfig", merged)

    @staticmethod
    def _to_dict(config: DictConfig) -> dict[str, Any]:
        """Convert a config to a dictionary without resolving interpolations."""
        container = OmegaConf.to_container(config, resolve=False)
        return cast("dict[str, Any]", container)

    @contextmanager
    def _oc_env_resolver_scope(self, *, allow_builtin: bool = False) -> Iterator[None]:
        """Temporarily register the configured oc.env resolver and restore the prior one."""
        resolver = self._oc_env_custom_resolver
        previous_resolver = OmegaConf._get_resolver("oc.env")
        try:
            if resolver is None and allow_builtin:
                OmegaConf.register_resolver("oc.env", oc.env, replace=True)
            elif resolver is None:
                OmegaConf.clear_resolver("oc.env")
            elif isinstance(resolver, tuple):
                resolver_fn, resolver_kwargs = resolver
                kwargs = dict(resolver_kwargs)
                kwargs.pop("replace", None)
                OmegaConf.register_resolver(
                    "oc.env", resolver_fn, replace=True, **kwargs
                )
            else:
                OmegaConf.register_resolver("oc.env", resolver, replace=True)
            yield
        finally:
            if previous_resolver is None:
                OmegaConf.clear_resolver("oc.env")
            else:
                BaseContainer._resolvers["oc.env"] = previous_resolver
