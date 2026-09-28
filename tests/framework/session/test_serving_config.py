from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest
import yaml
from omegaconf.errors import InterpolationResolutionError

from kedro.config.abstract_config import MissingConfigException
from kedro.config.omegaconf_config import OmegaConfigLoader
from kedro.framework.session._serving_config import (
    _ServingConfigLoader,
    _swapped_runtime_params,
    build_config_cache,
)

if TYPE_CHECKING:
    from pathlib import Path

_BASE_ENV = "base"
_RUN_ENV = "local"


def _write_yaml(filepath: Path, config: dict) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(yaml.dump(config))


@pytest.fixture
def conf_source(tmp_path) -> str:
    base = tmp_path / _BASE_ENV
    _write_yaml(
        base / "catalog.yml",
        {
            "cars": {
                "type": "pandas.CSVDataset",
                "filepath": "${runtime_params:filepath,'/default/cars.csv'}",
            },
            "boats": {
                "type": "${runtime_params:dataset_type,'pandas.CSVDataset'}",
                "filepath": "/default/boats.csv",
            },
        },
    )
    _write_yaml(
        base / "parameters.yml",
        {"model_options": {"test_size": "${runtime_params:test_size,0.2}"}},
    )
    _write_yaml(base / "credentials.yml", {"my_creds": {"account": "abc"}})
    _write_yaml(base / "globals.yml", {"env_name": "base"})
    return str(tmp_path)


@pytest.fixture
def persistent_loader(conf_source) -> OmegaConfigLoader:
    return OmegaConfigLoader(
        conf_source=conf_source,
        env=None,
        base_env=_BASE_ENV,
        default_run_env=_BASE_ENV,
        restrict_runtime_params_type_selection=True,
    )


@pytest.fixture
def second_conf_source(tmp_path_factory) -> str:
    """A second, independent project -- distinct defaults from ``conf_source``
    so cross-contamination between the two is easy to detect."""
    root = tmp_path_factory.mktemp("second_project")
    base = root / _BASE_ENV
    _write_yaml(
        base / "catalog.yml",
        {
            "cars": {
                "type": "pandas.CSVDataset",
                "filepath": "${runtime_params:filepath,'/other/cars.csv'}",
            },
            "labelled": {
                "type": "MemoryDataset",
                "copy_mode": "${globals:env_name}",
            },
        },
    )
    _write_yaml(base / "globals.yml", {"env_name": "other"})
    return str(root)


@pytest.fixture
def second_persistent_loader(second_conf_source) -> OmegaConfigLoader:
    return OmegaConfigLoader(
        conf_source=second_conf_source,
        env=None,
        base_env=_BASE_ENV,
        default_run_env=_BASE_ENV,
        restrict_runtime_params_type_selection=True,
    )


class TestBuildConfigCache:
    def test_caches_resolved_credentials_and_globals(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        assert cache.credentials == {"my_creds": {"account": "abc"}}
        assert cache.globals == {"env_name": "base"}

    def test_missing_credentials_default_to_empty_dict(self, tmp_path):
        _write_yaml(
            tmp_path / _BASE_ENV / "catalog.yml", {"cars": {"type": "MemoryDataset"}}
        )
        loader = OmegaConfigLoader(
            conf_source=str(tmp_path),
            env=None,
            base_env=_BASE_ENV,
            default_run_env=_BASE_ENV,
        )
        cache = build_config_cache(loader)
        assert cache.credentials == {}

    def test_raw_by_key_covers_every_non_special_config_pattern(self, conf_source):
        loader = OmegaConfigLoader(
            conf_source=conf_source,
            env=None,
            base_env=_BASE_ENV,
            default_run_env=_BASE_ENV,
            config_patterns={"spark": ["spark*"]},
        )
        cache = build_config_cache(loader)
        assert set(cache.raw_by_key) == {"catalog", "parameters", "spark"}

    def test_missing_config_dir_for_key_is_cached_as_none(self, conf_source):
        # The "does_not_exist" env directory doesn't exist, so reading the raw
        # per-file config for any key fails with MissingConfigException --
        # build_config_cache must record that as a cache miss, not raise.
        loader = OmegaConfigLoader(
            conf_source=conf_source,
            env="does_not_exist",
            base_env=_BASE_ENV,
            default_run_env=_BASE_ENV,
            restrict_runtime_params_type_selection=True,
        )
        cache = build_config_cache(loader)
        assert cache.raw_by_key["catalog"] is None
        assert cache.raw_by_key["parameters"] is None

    def test_cache_has_no_per_instance_lock(self, persistent_loader):
        # Resolving must be serialized process-wide (via the module-level
        # `_RESOLVE_LOCK`), not per-cache -- see TestMultipleSessions below
        # for why a per-cache lock isn't enough.
        cache = build_config_cache(persistent_loader)
        assert not hasattr(cache, "lock")


class TestServingConfigLoaderGetItem:
    def test_explicit_override_bypasses_cache(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(cache=cache, runtime_params={})
        loader["parameters"] = {"overridden": True}
        assert loader["parameters"] == {"overridden": True}

    def test_credentials_returns_a_copy(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(cache=cache, runtime_params={})
        creds = loader["credentials"]
        creds["my_creds"]["account"] = "mutated"
        assert cache.credentials["my_creds"]["account"] == "abc"

    def test_globals_returns_a_copy(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(cache=cache, runtime_params={})
        globals_ = loader["globals"]
        globals_["env_name"] = "mutated"
        assert cache.globals["env_name"] == "base"

    def test_unknown_key_raises_key_error(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(cache=cache, runtime_params={})
        with pytest.raises(KeyError, match="No config patterns were found"):
            loader["not_a_real_key"]

    def test_key_missing_at_cache_build_time_raises(self, conf_source):
        loader_source = OmegaConfigLoader(
            conf_source=conf_source,
            env="does_not_exist",
            base_env=_BASE_ENV,
            default_run_env=_BASE_ENV,
            restrict_runtime_params_type_selection=True,
        )
        cache = build_config_cache(loader_source)
        serving_loader = _ServingConfigLoader(cache=cache, runtime_params={})
        with pytest.raises(MissingConfigException, match="not available at cache"):
            serving_loader["catalog"]

    def test_resolves_with_this_requests_runtime_params(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(
            cache=cache, runtime_params={"filepath": "/tmp/mine.csv"}
        )
        assert loader["catalog"]["cars"]["filepath"] == "/tmp/mine.csv"

        params_loader = _ServingConfigLoader(
            cache=cache, runtime_params={"test_size": 0.4}
        )
        assert params_loader["parameters"]["model_options"]["test_size"] == 0.4

    def test_guard_blocks_runtime_params_driven_type(self, persistent_loader):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(
            cache=cache, runtime_params={"dataset_type": "os.system"}
        )
        with pytest.raises(InterpolationResolutionError):
            loader["catalog"]

    def test_restrict_runtime_params_type_selection_mirrors_persistent_loader(
        self, persistent_loader
    ):
        cache = build_config_cache(persistent_loader)
        loader = _ServingConfigLoader(cache=cache, runtime_params={})
        assert (
            loader.restrict_runtime_params_type_selection
            == persistent_loader.restrict_runtime_params_type_selection
            is True
        )

    def test_concurrent_requests_do_not_cross_contaminate(self, persistent_loader):
        cache = build_config_cache(persistent_loader)

        def worker(i: int) -> None:
            loader = _ServingConfigLoader(
                cache=cache,
                runtime_params={"filepath": f"/tmp/file_{i}.csv", "test_size": i / 100},
            )
            assert loader["catalog"]["cars"]["filepath"] == f"/tmp/file_{i}.csv"
            assert loader["parameters"]["model_options"]["test_size"] == i / 100

        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(worker, range(200)))

    def test_concurrent_malicious_requests_never_bypass_the_guard(
        self, persistent_loader
    ):
        cache = build_config_cache(persistent_loader)

        def worker(i: int) -> bool:
            malicious = i % 3 == 0
            runtime_params = {"filepath": f"/tmp/file_{i}.csv"}
            if malicious:
                runtime_params["dataset_type"] = "os.system"
            loader = _ServingConfigLoader(cache=cache, runtime_params=runtime_params)
            try:
                loader["catalog"]
                blocked = False
            except InterpolationResolutionError:
                blocked = True
            return malicious == blocked

        with ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(worker, range(300)))
        assert all(results)


class TestMultipleSessions:
    """OmegaConf's resolver registry is process-global: constructing a second
    persistent loader (e.g. a second `KedroServiceSession` in the same
    process) re-registers the "globals"/"runtime_params" resolver callbacks
    globally, which would silently corrupt an *already-built* cache's
    resolves unless every resolve reclaims its own loader's resolvers under
    a lock shared across every session, not just within one.
    """

    def test_second_session_does_not_hijack_the_first(
        self, persistent_loader, second_persistent_loader
    ):
        cache_a = build_config_cache(persistent_loader)
        # Building a second session's cache re-registers the process-global
        # resolvers to point at `second_persistent_loader`.
        build_config_cache(second_persistent_loader)

        request_loader = _ServingConfigLoader(
            cache=cache_a, runtime_params={"filepath": "/tmp/a-request.csv"}
        )
        assert request_loader["catalog"]["cars"]["filepath"] == "/tmp/a-request.csv"

    def test_globals_resolver_is_not_hijacked_either(
        self, persistent_loader, second_persistent_loader
    ):
        cache_a = build_config_cache(persistent_loader)
        build_config_cache(second_persistent_loader)

        request_loader = _ServingConfigLoader(cache=cache_a, runtime_params={})
        # `conf_source`'s globals.yml sets env_name to "base"; if the
        # resolver were still bound to `second_persistent_loader` this would
        # resolve to "other" instead (or raise, if it can't find the key).
        assert request_loader["globals"]["env_name"] == "base"

    def test_interleaved_requests_across_two_sessions_do_not_cross_contaminate(
        self, persistent_loader, second_persistent_loader
    ):
        cache_a = build_config_cache(persistent_loader)
        cache_b = build_config_cache(second_persistent_loader)

        def worker(i: int) -> None:
            if i % 2 == 0:
                loader = _ServingConfigLoader(
                    cache=cache_a, runtime_params={"filepath": f"a-{i}"}
                )
                assert loader["catalog"]["cars"]["filepath"] == f"a-{i}"
            else:
                loader = _ServingConfigLoader(
                    cache=cache_b, runtime_params={"filepath": f"b-{i}"}
                )
                assert loader["catalog"]["cars"]["filepath"] == f"b-{i}"

        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(worker, range(300)))


class TestSwappedRuntimeParams:
    def test_enter_sets_and_exit_restores_loader_state(self, persistent_loader):
        persistent_loader.runtime_params = {"original": True}
        persistent_loader._runtime_params_oc = "original_oc"
        persistent_loader._runtime_params_hits = {"original_hit"}

        with _swapped_runtime_params(persistent_loader, {"filepath": "/tmp/x.csv"}):
            assert persistent_loader.runtime_params == {"filepath": "/tmp/x.csv"}
            assert persistent_loader._runtime_params_oc is None
            assert persistent_loader._runtime_params_hits == set()

        assert persistent_loader.runtime_params == {"original": True}
        assert persistent_loader._runtime_params_oc == "original_oc"
        assert persistent_loader._runtime_params_hits == {"original_hit"}

    def test_none_runtime_params_defaults_to_empty_dict(self, persistent_loader):
        with _swapped_runtime_params(persistent_loader, None):
            assert persistent_loader.runtime_params == {}
