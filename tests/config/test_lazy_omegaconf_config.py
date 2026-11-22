from __future__ import annotations

import copy
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from omegaconf import OmegaConf
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import (
    InterpolationResolutionError,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
)

from kedro.config import (
    LazyOmegaConfigLoader,
    MissingConfigException,
    OmegaConfigLoader,
)
from kedro.utils import KedroExperimentalWarning

if TYPE_CHECKING:
    from pathlib import Path


def _write_yaml(filepath: Path, config: dict[str, Any]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(yaml.safe_dump(config))


def _loader(
    root: Path,
    interpolation_scope: str = "environment",
    runtime_params: dict[str, Any] | None = None,
    **kwargs: Any,
) -> LazyOmegaConfigLoader:
    (root / "base").mkdir(exist_ok=True)
    (root / "local").mkdir(exist_ok=True)
    return LazyOmegaConfigLoader(
        conf_source=root,
        base_env="base",
        default_run_env="local",
        interpolation_scope=interpolation_scope,
        runtime_params=runtime_params,
        **kwargs,
    )


class TestLazyOmegaConfigLoader:
    def test_class_warns_once_on_instantiation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 1})
        monkeypatch.setattr(
            LazyOmegaConfigLoader, "__kedro_experimental_warned__", False, raising=False
        )

        with pytest.warns(
            KedroExperimentalWarning, match="LazyOmegaConfigLoader is experimental"
        ) as caught:
            loader = _loader(tmp_path, interpolation_scope="environment")
        assert len(caught) == 1

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert loader["parameters"] == {"value": 1}
            loader.preload()
            loader.with_runtime_params()
            loader.get_unresolved_config("parameters")
            _loader(tmp_path)

        assert not any(
            issubclass(warning.category, KedroExperimentalWarning) for warning in caught
        )

    def test_invalid_interpolation_scope_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="interpolation_scope"):
            LazyOmegaConfigLoader(tmp_path, interpolation_scope="invalid")

    def test_remote_config_root_is_stored(self, mocker) -> None:
        mocker.patch.object(
            LazyOmegaConfigLoader,
            "_initialise_filesystem_and_protocol",
            return_value=(object(), "s3"),
        )

        loader = LazyOmegaConfigLoader("s3://bucket/config", base_env="base")

        assert loader._remote_root_path == "bucket/config"

    def test_constructor_does_not_replace_global_runtime_resolver(
        self, tmp_path: Path, mocker
    ) -> None:
        register = mocker.spy(OmegaConf, "register_resolver")
        loader = _loader(
            tmp_path,
            custom_resolvers={
                "globals": lambda key: key,
                "runtime_params": lambda key: key,
                "oc.env": lambda key: key,
            },
        )

        registered_names = {
            call.kwargs.get("name", call.args[0]) for call in register.call_args_list
        }
        assert not {"globals", "runtime_params"} & registered_names
        assert loader._globals_loaded is False

    def test_interpolation_scope_environment_matches_omega_config_loader(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"param1": "${param2}", "param2": "base"},
        )
        _write_yaml(tmp_path / "local" / "parameters.yml", {"param2": "local"})

        expected = OmegaConfigLoader(
            tmp_path, base_env="base", default_run_env="local"
        )["parameters"]
        actual = _loader(tmp_path, interpolation_scope="environment")["parameters"]

        assert actual == expected == {"param1": "base", "param2": "local"}

    def test_default_interpolation_scope_matches_omega_config_loader(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"param1": "${param2}", "param2": "base"},
        )
        _write_yaml(tmp_path / "local" / "parameters.yml", {"param2": "local"})

        loader = LazyOmegaConfigLoader(
            tmp_path, base_env="base", default_run_env="local"
        )

        assert loader.interpolation_scope == "environment"
        assert loader["parameters"] == {"param1": "base", "param2": "local"}

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_replacing_config_patterns_keeps_globals(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(tmp_path / "base" / "globals.yml", {"bucket": "prod"})
        _write_yaml(
            tmp_path / "base" / "catalog.yml", {"ds": {"path": "${globals:bucket}"}}
        )
        loader = _loader(tmp_path, interpolation_scope=scope)

        loader.config_patterns = {"catalog": ["catalog*"]}

        assert loader["catalog"] == {"ds": {"path": "prod"}}
        assert loader["globals"] == {"bucket": "prod"}
        assert "globals" not in loader.config_patterns

    def test_interpolation_scope_merged_resolves_after_environment_merge(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"param1": "${param2}", "param2": "base"},
        )
        _write_yaml(tmp_path / "local" / "parameters.yml", {"param2": "local"})

        assert _loader(tmp_path, interpolation_scope="merged")["parameters"] == {
            "param1": "local",
            "param2": "local",
        }

    def test_soft_merge_strategy_preserves_nested_environment_keys(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"x": {"a": 1}})
        _write_yaml(tmp_path / "local" / "parameters.yml", {"x": {"b": 2}})

        result = _loader(
            tmp_path,
            merge_strategy={"parameters": "soft"},
        )["parameters"]

        assert result == {"x": {"a": 1, "b": 2}}

    def test_global_interpolation_resolves_from_globals(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "globals.yml", {"test_value": 42})
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${globals:test_value}"},
        )

        assert _loader(tmp_path)["parameters"] == {"value": 42}

    def test_globals_override_updates_per_run_view_only(self, tmp_path: Path) -> None:
        loader = _loader(tmp_path)
        loader.preload()
        view = loader.with_runtime_params()
        view["globals"] = {"run": "view"}

        assert view["globals"] == {"run": "view"}
        assert loader["globals"] == {}

    def test_concurrent_first_globals_load_is_safe(self, tmp_path: Path) -> None:
        loader = _loader(tmp_path)
        barrier = threading.Barrier(8)

        def load_globals(_: int) -> dict[str, Any]:
            barrier.wait()
            return loader["globals"]

        with ThreadPoolExecutor(max_workers=8) as executor:
            assert list(executor.map(load_globals, range(8))) == [{}] * 8

    def test_globals_loaded_while_waiting_for_lock_skips_duplicate_load(
        self, tmp_path: Path, mocker
    ) -> None:
        # The concurrent test above (test_concurrent_first_globals_load_is_safe) is scheduler-dependent: callers may see the flag
        # before taking the lock. Set it on lock entry to reliably cover the second check.
        # This avoids the CI test coverage being flaky due to race conditions
        loader = _loader(tmp_path)

        def mark_globals_loaded() -> None:
            loader._globals = {"loaded": "by another thread"}
            loader._globals_loaded = True

        lock = mocker.patch.object(loader, "_globals_lock")
        lock.__enter__.side_effect = mark_globals_loaded

        loader._ensure_globals()

        assert loader._globals == {"loaded": "by another thread"}

    def test_custom_resolver_is_applied(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${double:21}"},
        )
        loader = _loader(tmp_path, custom_resolvers={"double": lambda value: value * 2})

        assert loader["parameters"] == {"value": 42}

    @pytest.mark.parametrize(
        "resolver",
        [
            lambda variable: "custom-value",
            (lambda variable: "custom-value", {"use_cache": True}),
        ],
    )
    def test_custom_oc_env_resolver_is_applied(
        self, tmp_path: Path, resolver: Any
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${oc.env:LAZY_CUSTOM}"},
        )
        loader = _loader(tmp_path, custom_resolvers={"oc.env": resolver})

        assert loader["parameters"] == {"value": "custom-value"}

    def test_oc_env_resolver_is_restored_after_custom_resolution(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${oc.env:LAZY_CUSTOM}"},
        )
        original_resolver = OmegaConf._get_resolver("oc.env")
        loader = _loader(
            tmp_path,
            custom_resolvers={"oc.env": lambda variable: "custom-value"},
        )

        assert loader["parameters"] == {"value": "custom-value"}
        assert OmegaConf._get_resolver("oc.env") is original_resolver

    def test_builtin_oc_env_resolver_is_unchanged_by_parameter_resolution(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 1})
        original_resolver = OmegaConf._get_resolver("oc.env")
        loader = _loader(tmp_path)

        assert loader["parameters"] == {"value": 1}
        assert OmegaConf._get_resolver("oc.env") is original_resolver

    def test_oc_env_resolver_is_restored_when_an_existing_resolver_is_present(
        self, tmp_path: Path
    ) -> None:
        # OmegaConf may start without an oc.env resolver, so the test above only covers
        # restoring None. Register one here to reliably cover restoring an existing one.
        # this is required to make the CI test coverage non flaky

        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${oc.env:LAZY_CUSTOM}"},
        )
        original_resolver = OmegaConf._get_resolver("oc.env")

        def previous_resolver(variable: str) -> str:
            return "previous-value"

        OmegaConf.register_resolver("oc.env", previous_resolver, replace=True)
        registered_resolver = OmegaConf._get_resolver("oc.env")
        loader = _loader(
            tmp_path,
            custom_resolvers={"oc.env": lambda variable: "custom-value"},
        )

        try:
            assert loader["parameters"] == {"value": "custom-value"}
            assert OmegaConf._get_resolver("oc.env") is registered_resolver
        finally:
            if original_resolver is None:
                OmegaConf.clear_resolver("oc.env")
            else:
                BaseContainer._resolvers["oc.env"] = original_resolver

    def test_oc_env_resolver_is_not_used_outside_credentials(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {"dataset": {"file_path": "${oc.env:LAZY_DATASET}"}},
        )
        monkeypatch.setenv("LAZY_DATASET", "dataset.csv")
        loader = _loader(tmp_path)

        with pytest.raises(UnsupportedInterpolationType):
            loader["catalog"]

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    @pytest.mark.parametrize("key", ["credentials", "parameters"])
    @pytest.mark.parametrize("registered", [False, True])
    def test_oc_env_is_restored_after_failed_resolution(
        self, tmp_path: Path, scope: str, key: str, registered: bool
    ) -> None:
        _write_yaml(tmp_path / "base" / f"{key}.yml", {"value": "${oc.env:FAIL}"})
        original_resolver = OmegaConf._get_resolver("oc.env")

        def fail_resolver(variable: str) -> str:
            raise ValueError("resolver failed")

        try:
            if registered:
                OmegaConf.register_resolver(
                    "oc.env", lambda variable: "previous", replace=True
                )
            else:
                OmegaConf.clear_resolver("oc.env")
            previous_resolver = OmegaConf._get_resolver("oc.env")
            loader = _loader(
                tmp_path,
                interpolation_scope=scope,
                custom_resolvers={"oc.env": fail_resolver},
            )

            with pytest.raises(InterpolationResolutionError, match="resolver failed"):
                loader[key]

            assert OmegaConf._get_resolver("oc.env") is previous_resolver
        finally:
            if original_resolver is None:
                OmegaConf.clear_resolver("oc.env")
            else:
                BaseContainer._resolvers["oc.env"] = original_resolver

    def test_run_view_can_add_config_patterns(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "spark.yml", {"spark.executor": "2g"})
        view = _loader(tmp_path).with_runtime_params()
        view.config_patterns["spark"] = ["spark*"]

        assert view["spark"] == {"spark.executor": "2g"}

    def test_preload_resolves_credentials_environment_variables(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "credentials.yml",
            {"database": {"user": "${oc.env:LAZY_USER}"}},
        )
        monkeypatch.setenv("LAZY_USER", "kedro-user")
        loader = _loader(tmp_path)
        loader.preload()

        assert loader.with_runtime_params({"unused": True})["credentials"] == {
            "database": {"user": "kedro-user"}
        }

    def test_credentials_use_the_original_loader_runtime_params(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "credentials.yml",
            {"db": {"user": "${runtime_params:user, default_user}"}},
        )
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 1})
        loader = _loader(tmp_path, runtime_params={"user": "original"})
        first = loader.with_runtime_params({"user": "first"})
        second = loader.with_runtime_params({"user": "second"})
        first["parameters"]

        assert first["credentials"] == {"db": {"user": "original"}}
        assert second["credentials"] == {"db": {"user": "original"}}
        assert loader["credentials"] == {"db": {"user": "original"}}

    def test_credentials_use_their_loader_globals_after_another_loader_resolves(
        self, tmp_path: Path
    ) -> None:
        loaders = {}
        for name in ("a", "b"):
            root = tmp_path / name
            _write_yaml(root / "base" / "globals.yml", {"owner": name})
            _write_yaml(root / "base" / "parameters.yml", {"value": 1})
            _write_yaml(
                root / "base" / "credentials.yml", {"db": {"user": "${globals:owner}"}}
            )
            loaders[name] = _loader(root)
        loaders["a"]["parameters"]
        loaders["b"]["parameters"]

        assert loaders["a"]["credentials"] == {"db": {"user": "a"}}

    def test_missing_config_key_raises_missing_config_exception(
        self, tmp_path: Path
    ) -> None:
        loader = _loader(tmp_path)

        with pytest.raises(MissingConfigException):
            loader["parameters"]

    def test_unknown_config_key_raises_key_error(self, tmp_path: Path) -> None:
        loader = _loader(tmp_path)

        with pytest.raises(KeyError, match="No config patterns were found"):
            loader["unknown"]

    def test_missing_environment_error_is_cached(self, tmp_path: Path, mocker) -> None:
        (tmp_path / "base").mkdir()
        loader = LazyOmegaConfigLoader(
            tmp_path,
            base_env="base",
            default_run_env="missing",
            interpolation_scope="merged",
        )
        read_raw_config = mocker.spy(loader, "_read_raw_config")

        for _ in range(2):
            with pytest.raises(MissingConfigException):
                loader._get_raw_config("parameters")

        read_raw_config.assert_called_once_with("parameters")

    def test_preload_defers_missing_config_error_until_access(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "base").mkdir()
        (tmp_path / "local").mkdir()
        loader = _loader(tmp_path)

        loader.preload()
        with pytest.raises(MissingConfigException):
            loader["parameters"]

    def test_preload_tolerates_missing_run_environment(self, tmp_path: Path) -> None:
        (tmp_path / "base").mkdir()
        loader = LazyOmegaConfigLoader(
            tmp_path,
            base_env="base",
            default_run_env="missing",
            interpolation_scope="merged",
        )

        loader.preload()

        assert loader["globals"] == {}
        with pytest.raises(MissingConfigException):
            loader["parameters"]

    def test_missing_credentials_preload_defaults_to_empty_mapping(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "base").mkdir()
        loader = _loader(tmp_path)
        loader.preload()

        assert loader["credentials"] == {}

    def test_missing_config_files_raise_on_access(self, tmp_path: Path) -> None:
        (tmp_path / "base").mkdir()
        (tmp_path / "local").mkdir()
        loader = _loader(tmp_path)

        with pytest.raises(MissingConfigException, match="No files"):
            loader["parameters"]

    def test_base_environment_only_is_supported(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 3})
        loader = LazyOmegaConfigLoader(
            tmp_path,
            base_env="base",
            default_run_env="base",
            interpolation_scope="merged",
        )

        assert loader["parameters"] == {"value": 3}

    def test_unsupported_merge_strategy_raises(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 1})
        _write_yaml(tmp_path / "local" / "parameters.yml", {"value": 2})
        loader = _loader(tmp_path, merge_strategy={"parameters": "invalid"})

        with pytest.raises(ValueError, match="Merging strategy invalid not supported"):
            loader["parameters"]

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_runtime_params_are_not_supported_in_globals(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "globals.yml",
            {"value": "${runtime_params:value}"},
        )
        loader = _loader(tmp_path, interpolation_scope=scope)

        with pytest.raises(
            UnsupportedInterpolationType, match="not supported for globals"
        ):
            loader["globals"]

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_unknown_resolver_error_is_preserved(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${lazy_unknown_resolver:value}"},
        )
        loader = _loader(tmp_path, interpolation_scope=scope)

        with pytest.raises(
            UnsupportedInterpolationType,
            match="Unsupported interpolation type lazy_unknown_resolver",
        ):
            loader["parameters"]

    @pytest.mark.parametrize(
        ("scope", "expected"),
        [
            ("environment", {"x": {"b": 5}, "y": 2}),
            ("merged", {"x": {"a": 1, "b": 5}, "y": 2}),
        ],
    )
    def test_runtime_params_destructive_merge_edge_case(
        self, tmp_path: Path, scope: str, expected: dict[str, Any]
    ) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"x": {"a": 1}})
        _write_yaml(tmp_path / "local" / "parameters.yml", {"y": 2})

        result = _loader(
            tmp_path,
            interpolation_scope=scope,
            runtime_params={"x": {"b": 5}},
        )["parameters"]

        assert result == expected

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_runtime_params_are_returned_with_parameters(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"report_label": "Report for ${runtime_params:customer_id}"},
        )
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()

        run = loader.with_runtime_params({"customer_id": "customer-001"})

        expected = {
            "report_label": "Report for customer-001",
            "customer_id": "customer-001",
        }
        assert run["parameters"] == expected
        assert run.runtime_params == {"customer_id": "customer-001"}
        assert (
            OmegaConfigLoader(
                tmp_path,
                base_env="base",
                default_run_env="local",
                runtime_params={"customer_id": "customer-001"},
            )["parameters"]
            == expected
        )

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_runtime_params_override_existing_parameter_keys(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {
                "customer_id": "yaml-001",
                "report_label": "Report for ${runtime_params:customer_id}",
            },
        )
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()

        run = loader.with_runtime_params(
            {
                "customer_id": "request-002",
                "runtime_only": "x",
            }
        )

        expected = {
            "customer_id": "request-002",
            "report_label": "Report for request-002",
            "runtime_only": "x",
        }
        assert run["parameters"] == expected
        assert (
            OmegaConfigLoader(
                tmp_path,
                base_env="base",
                default_run_env="local",
                runtime_params={"customer_id": "request-002", "runtime_only": "x"},
            )["parameters"]
            == expected
        )

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_runtime_params_not_propagate_non_parameters_config(
        self, tmp_path: Path, scope: str, monkeypatch
    ) -> None:
        """`catalog`, `credentials` and custom configs are resolved with
        `runtime_params` but never receive its keys; only `parameters` does."""
        monkeypatch.setenv("LAZY_USER", "kedro-user")
        _write_yaml(tmp_path / "base" / "parameters.yml", {"param1": 1})
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {
                "companies": {
                    "type": "MemoryDataset",
                    "filepath": "data/${runtime_params:folder}/companies.csv",
                }
            },
        )
        _write_yaml(
            tmp_path / "base" / "credentials.yml",
            {"database": {"user": "${oc.env:LAZY_USER}"}},
        )
        _write_yaml(
            tmp_path / "base" / "spark.yml", {"master": "${runtime_params:master}"}
        )
        loader = _loader(
            tmp_path,
            interpolation_scope=scope,
            config_patterns={"spark": ["spark*", "spark*/**", "**/spark*"]},
        )

        run = loader.with_runtime_params(
            {
                "test_env": "dummy",
                "folder": "raw",
                "master": "local[2]",
            }
        )

        assert "test_env" in run["parameters"]
        assert run["catalog"] == {
            "companies": {
                "type": "MemoryDataset",
                "filepath": "data/raw/companies.csv",
            }
        }
        assert run["credentials"] == {"database": {"user": "kedro-user"}}
        assert run["spark"] == {"master": "local[2]"}

    def test_run_views_resolve_independently_and_do_not_mutate_snapshot(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"learning_rate": "${runtime_params:learning_rate,0.1}"},
        )
        loader = _loader(tmp_path)
        loader.preload()
        low = loader.with_runtime_params({"learning_rate": 0.01})
        high = loader.with_runtime_params({"learning_rate": 0.9})

        assert low["parameters"]["learning_rate"] == 0.01
        assert high["parameters"]["learning_rate"] == 0.9
        assert loader["parameters"]["learning_rate"] == 0.1

        low["globals"] = {"run": "low"}
        high["globals"] = {"run": "high"}
        assert low["globals"] == {"run": "low"}
        assert high["globals"] == {"run": "high"}

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    @pytest.mark.parametrize("key", ["parameters", "catalog"])
    def test_resolving_a_run_view_does_not_mutate_raw_snapshot(
        self, tmp_path: Path, scope: str, key: str
    ) -> None:
        _write_yaml(tmp_path / "base" / f"{key}.yml", {"a": {"type": "A"}})
        _write_yaml(tmp_path / "base" / f"{key}_extra.yml", {"b": {"type": "B"}})
        _write_yaml(tmp_path / "local" / f"{key}.yml", {"c": {"type": "C"}})
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()
        raw = loader._get_raw_config(key)
        base_before = copy.deepcopy(raw.base_configs)
        env_before = copy.deepcopy(raw.env_configs)

        loader.with_runtime_params({"only_in_this_run": "x"})[key]

        assert raw.base_configs == base_before
        assert raw.env_configs == env_before

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_runtime_params_do_not_leak_into_later_runs(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"label": "${runtime_params:x,'default'}"},
        )
        _write_yaml(tmp_path / "local" / "parameters.yml", {"other": 1})
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()

        loader.with_runtime_params({"only_in_first_run": "x", "x": "first"})[
            "parameters"
        ]

        expected = {"label": "default", "other": 1}
        assert loader.with_runtime_params({})["parameters"] == expected
        assert loader["parameters"] == expected

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    @pytest.mark.parametrize("key", ["catalog", "parameters", "spark"])
    def test_underscore_prefixed_template_keys_match_omega_config_loader(
        self, tmp_path: Path, scope: str, key: str
    ) -> None:
        """Only `parameters` keeps `_`-prefixed keys; they are templates elsewhere."""
        patterns = {"spark": ["spark*", "spark*/**", "**/spark*"]}
        _write_yaml(
            tmp_path / "base" / f"{key}.yml",
            {"_template": {"value": 1}, "first": "${_template.value}"},
        )
        _write_yaml(tmp_path / "local" / f"{key}.yml", {"second": 2})

        expected = OmegaConfigLoader(
            tmp_path,
            base_env="base",
            default_run_env="local",
            config_patterns=patterns,
        )[key]
        actual = _loader(tmp_path, interpolation_scope=scope, config_patterns=patterns)[
            key
        ]

        assert actual == expected
        assert ("_template" in actual) is (key == "parameters")

    def test_merged_scope_merges_environments_once_across_runs(
        self, tmp_path: Path, mocker
    ) -> None:
        _write_yaml(tmp_path / "base" / "catalog.yml", {"a": {"type": "A"}})
        _write_yaml(tmp_path / "local" / "catalog.yml", {"b": {"type": "B"}})
        loader = _loader(tmp_path, interpolation_scope="merged")
        merge = mocker.spy(loader, "_merge_raw_environments")
        loader.preload()
        merges_after_preload = merge.call_count

        for index in range(3):
            loader.with_runtime_params({"run": index})["catalog"]

        assert merges_after_preload >= 1
        assert merge.call_count == merges_after_preload

    def test_merged_cache_follows_merge_strategy_changes(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"x": {"a": 1}})
        _write_yaml(tmp_path / "local" / "parameters.yml", {"x": {"b": 2}})
        loader = _loader(tmp_path, interpolation_scope="merged")

        assert loader["parameters"] == {"x": {"b": 2}}
        loader.merge_strategy = {"parameters": "soft"}
        assert loader["parameters"] == {"x": {"a": 1, "b": 2}}

    def test_preload_surfaces_merge_errors_in_merged_scope(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 1})
        _write_yaml(tmp_path / "local" / "parameters.yml", {"value": 2})
        loader = _loader(
            tmp_path,
            interpolation_scope="merged",
            merge_strategy={"parameters": "invalid"},
        )

        with pytest.raises(ValueError, match="Merging strategy invalid not supported"):
            loader.preload()

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_cached_resolver_results_do_not_leak_between_runs(
        self, tmp_path: Path, scope: str
    ) -> None:
        calls: list[int] = []

        def counter() -> int:
            calls.append(1)
            return len(calls)

        _write_yaml(tmp_path / "base" / "catalog.yml", {"a": {"id": "${counter:}"}})
        _write_yaml(tmp_path / "local" / "catalog.yml", {"b": {"id": "${counter:}"}})
        loader = _loader(
            tmp_path,
            interpolation_scope=scope,
            custom_resolvers={"counter": (counter, {"use_cache": True})},
        )
        loader.preload()

        first = loader.with_runtime_params({})["catalog"]
        second = loader.with_runtime_params({})["catalog"]

        assert first != second

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_concurrent_resolution_with_absolute_interpolations(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {
                "shared": {"folder": "${runtime_params:folder}"},
                **{
                    f"dataset_{index}": {
                        "type": "MemoryDataset",
                        "path": f"${{shared.folder}}/{index}",
                    }
                    for index in range(40)
                },
            },
        )
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()

        def resolve(index: int) -> bool:
            catalog = loader.with_runtime_params({"folder": f"run-{index}"})["catalog"]
            return all(
                entry["path"].startswith(f"run-{index}/")
                for name, entry in catalog.items()
                if name.startswith("dataset_")
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            assert all(executor.map(resolve, range(60)))

    def test_run_view_shares_raw_cache_but_copies_override_state(
        self, tmp_path: Path
    ) -> None:
        loader = _loader(tmp_path)
        loader.preload()
        loader["parameters"] = {"owner": "base", "nested": {"value": 1}}
        view = loader.with_runtime_params()

        assert view._raw_config_cache is loader._raw_config_cache
        assert view.data is not loader.data
        assert view._resolved_static_config is not loader._resolved_static_config
        view["parameters"] = {"owner": "view"}
        assert loader["parameters"] == {"owner": "base", "nested": {"value": 1}}

        view = loader.with_runtime_params()
        view["parameters"]["nested"]["value"] = 2
        assert loader["parameters"]["nested"]["value"] == 1

    def test_preload_does_not_resolve_parameters(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${runtime_params:value}"},
        )
        loader = _loader(tmp_path)

        loader.preload()
        with pytest.raises(
            InterpolationResolutionError,
            match=r"with_runtime_params\(\.\.\.\).*default in the interpolation",
        ):
            loader["parameters"]

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_concurrent_run_views_do_not_cross_contaminate(
        self, tmp_path: Path, scope: str
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${runtime_params:value}"},
        )
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()

        def resolve(value: int) -> bool:
            view = loader.with_runtime_params({"value": value})
            return view["parameters"]["value"] == value

        with ThreadPoolExecutor(max_workers=8) as executor:
            assert all(executor.map(resolve, range(80)))

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    @pytest.mark.parametrize("first_run", ["original", "temporary"])
    def test_same_loader_waits_before_capturing_runtime_state(
        self, tmp_path: Path, mocker, first_run: str, scope: str
    ) -> None:
        """A waiting call must not capture another call's temporary state."""
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {
                "dataset": {
                    "a_run": "${runtime_params:run}",
                    "b_pause": "${pause_same_loader:}",
                }
            },
        )
        paused = threading.Event()
        waiting = threading.Event()
        resume = threading.Event()

        def pause_resolution() -> str:
            paused.set()
            if not resume.wait(timeout=10):
                raise TimeoutError("Resolution was not resumed")
            return "resumed"

        loader = _loader(
            tmp_path,
            interpolation_scope=scope,
            runtime_params={"run": "original"},
            custom_resolvers={"pause_same_loader": pause_resolution},
        )
        try:
            loader.preload()
            lock = threading.Lock()

            class TrackedLock:
                def __enter__(self) -> None:
                    if paused.is_set():
                        waiting.set()
                    lock.acquire()

                def __exit__(self, *args: Any) -> None:
                    lock.release()

            mocker.patch(
                "kedro.config.lazy_omegaconf_config._RESOLVE_LOCK", TrackedLock()
            )

            # Pause the first call after it has resolved its temporary parameter.
            # Wait until the second call reaches the lock before letting it finish.
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(
                    loader._resolve_config, "catalog", {"run": first_run}
                )
                try:
                    assert paused.wait(timeout=10)
                    second = executor.submit(lambda: loader["catalog"])
                    assert waiting.wait(timeout=10)
                finally:
                    resume.set()
                assert first.result(timeout=10)["dataset"]["a_run"] == first_run
                assert second.result(timeout=10)["dataset"]["a_run"] == "original"

            assert loader.runtime_params == {"run": "original"}
            assert loader._runtime_params_oc is None
            assert loader._runtime_params_hits == set()
        finally:
            OmegaConf.clear_resolver("pause_same_loader")

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_override_access_during_resolution_keeps_run_resolver(
        self, tmp_path: Path, scope: str
    ) -> None:
        """Reading an override must not replace another run's active resolver.

        OmegaConf's resolver registry is process-global. Previously,
        LazyOmegaConfigLoader.__getitem__ delegated explicit override reads to
        OmegaConfigLoader.__getitem__, which registered the reading view's
        runtime_params resolver without taking the lazy loader's resolution lock.

        A pauses during catalog resolution with its resolver registered. B then
        reads an explicit override before A resumes. Previously, B's read replaced
        A's resolver, so A's remaining runtime_params interpolation returned "B".
        The views' runtime parameter dictionaries were never shared or modified.
        """
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {
                "dataset": {
                    "a_pause": "${pause_during_resolution:}",
                    "b_run": "${runtime_params:run}",
                }
            },
        )
        paused = threading.Event()
        resume = threading.Event()

        def pause_resolution() -> str:
            paused.set()
            if not resume.wait(timeout=10):
                raise TimeoutError("Resolution was not resumed")
            return "resumed"

        loader = _loader(
            tmp_path,
            interpolation_scope=scope,
            custom_resolvers={"pause_during_resolution": pause_resolution},
        )
        try:
            view_a = loader.with_runtime_params({"run": "A"})
            view_b = loader.with_runtime_params({"run": "B"})
            view_b["parameters"] = {"marker": "override"}

            # Pause A while it holds the resolver lock, then read B's override
            # on another thread before A resolves its runtime parameter.
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = executor.submit(lambda: view_a["catalog"])
                try:
                    assert paused.wait(timeout=10)
                    assert view_b["parameters"] == {"marker": "override"}
                finally:
                    resume.set()
                assert result.result(timeout=10) == {
                    "dataset": {"a_pause": "resumed", "b_run": "A"}
                }
        finally:
            OmegaConf.clear_resolver("pause_during_resolution")

    def test_catalog_type_guard_uses_each_run_runtime_params(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {"dataset": {"type": "${runtime_params:dataset_type}"}},
        )
        loader = _loader(
            tmp_path, restrict_runtime_params_type_selection=True
        ).with_runtime_params({"dataset_type": "MemoryDataset"})

        with pytest.raises(InterpolationResolutionError, match="not permitted"):
            loader["catalog"]

    def test_run_view_can_override_catalog_type_guard(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base" / "catalog.yml",
            {"dataset": {"type": "${runtime_params:dataset_type}"}},
        )
        loader = _loader(
            tmp_path,
            restrict_runtime_params_type_selection=True,
        ).with_runtime_params(
            {"dataset_type": "MemoryDataset"},
            restrict_runtime_params_type_selection=False,
        )

        assert loader["catalog"] == {"dataset": {"type": "MemoryDataset"}}

    def test_preload_freezes_raw_config_but_explicit_override_bypasses_resolution(
        self, tmp_path: Path
    ) -> None:
        filepath = tmp_path / "base" / "parameters.yml"
        _write_yaml(filepath, {"value": 1})
        loader = _loader(tmp_path)
        loader.preload()
        _write_yaml(filepath, {"value": 2})
        assert loader["parameters"] == {"value": 1}

        loader["parameters"] = {"value": "${runtime_params:value}"}
        assert loader["parameters"] == {"value": "${runtime_params:value}"}

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_preload_during_resolution_preserves_run_snapshot(
        self, tmp_path: Path, mocker, scope: str
    ) -> None:
        filepath = tmp_path / "base" / "catalog.yml"

        def write_catalog(version: str) -> None:
            _write_yaml(
                filepath,
                {
                    "dataset": {
                        "a_pause": "${pause_preload_resolution:}",
                        "run": "${runtime_params:run}",
                        "version": version,
                    }
                },
            )

        paused = threading.Event()
        waiting = threading.Event()
        resume = threading.Event()

        def pause_resolution() -> str:
            paused.set()
            if not resume.wait(timeout=10):
                raise TimeoutError("Resolution was not resumed")
            return "resumed"

        write_catalog("old")
        loader = _loader(
            tmp_path,
            interpolation_scope=scope,
            custom_resolvers={"pause_preload_resolution": pause_resolution},
        )
        try:
            loader.preload()
            old_view = loader.with_runtime_params({"run": "old"})
            lock = threading.Lock()

            class TrackedLock:
                def __enter__(self) -> None:
                    if paused.is_set():
                        waiting.set()
                    lock.acquire()

                def __exit__(self, *args: Any) -> None:
                    lock.release()

            mocker.patch(
                "kedro.config.lazy_omegaconf_config._RESOLVE_LOCK", TrackedLock()
            )

            # Start preload only after the old view is resolving, and wait until
            # preload reaches the lock before allowing that resolution to finish.
            with ThreadPoolExecutor(max_workers=2) as executor:
                resolving = executor.submit(lambda: old_view["catalog"])
                try:
                    assert paused.wait(timeout=10)
                    write_catalog("new")
                    preloading = executor.submit(loader.preload)
                    assert waiting.wait(timeout=10)
                finally:
                    resume.set()
                assert resolving.result(timeout=10)["dataset"] == {
                    "a_pause": "resumed",
                    "run": "old",
                    "version": "old",
                }
                preloading.result(timeout=10)

            assert old_view["catalog"]["dataset"]["version"] == "old"
            new_view = loader.with_runtime_params({"run": "new"})
            assert new_view["catalog"]["dataset"]["version"] == "new"
        finally:
            OmegaConf.clear_resolver("pause_preload_resolution")

    @pytest.mark.parametrize("scope", ["environment", "merged"])
    def test_second_preload_rereads_files(self, tmp_path: Path, scope: str) -> None:
        filepath = tmp_path / "base" / "parameters.yml"
        _write_yaml(filepath, {"value": 1})
        _write_yaml(tmp_path / "base" / "globals.yml", {"g": 1})
        _write_yaml(tmp_path / "base" / "credentials.yml", {"token": 1})
        loader = _loader(tmp_path, interpolation_scope=scope)
        loader.preload()

        _write_yaml(filepath, {"value": 2})
        _write_yaml(tmp_path / "base" / "globals.yml", {"g": 2})
        _write_yaml(tmp_path / "base" / "credentials.yml", {"token": 2})
        assert loader["parameters"] == {"value": 1}
        loader.preload()

        assert loader["parameters"] == {"value": 2}
        assert loader["globals"] == {"g": 2}
        assert loader["credentials"] == {"token": 2}
        assert loader.with_runtime_params({})["parameters"] == {"value": 2}

    def test_failed_preload_keeps_previous_snapshot(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 1})
        loader = _loader(tmp_path)
        loader.preload()

        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": 2})
        _write_yaml(tmp_path / "base" / "parameters_extra.yml", {"value": 3})
        with pytest.raises(ValueError, match="Duplicate"):
            loader.preload()

        assert loader["parameters"] == {"value": 1}

    def test_views_keep_the_snapshot_they_were_created_from(
        self, tmp_path: Path
    ) -> None:
        filepath = tmp_path / "base" / "parameters.yml"
        _write_yaml(filepath, {"value": 1})
        loader = _loader(tmp_path)
        loader.preload()
        old_view = loader.with_runtime_params({})

        _write_yaml(filepath, {"value": 2})
        loader.preload()
        new_view = loader.with_runtime_params({})

        assert old_view["parameters"] == {"value": 1}
        assert new_view["parameters"] == {"value": 2}

    def test_preload_keeps_explicit_overrides(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base" / "globals.yml", {"g": "file"})
        _write_yaml(tmp_path / "base" / "credentials.yml", {"token": "file"})
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": "${globals:g}"})
        loader = _loader(tmp_path)
        loader["globals"] = {"g": "override"}
        loader["credentials"] = {"token": "override"}

        loader.preload()

        assert loader["globals"] == {"g": "override"}
        assert loader["credentials"] == {"token": "override"}
        assert loader["parameters"] == {"value": "override"}

    def test_deleting_an_override_makes_preload_read_files_again(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(tmp_path / "base" / "globals.yml", {"g": "file"})
        _write_yaml(tmp_path / "base" / "parameters.yml", {"value": "${globals:g}"})
        loader = _loader(tmp_path)
        loader["globals"] = {"g": "override"}
        loader.preload()
        assert loader["parameters"] == {"value": "override"}

        del loader["globals"]
        loader.preload()

        assert loader["parameters"] == {"value": "file"}

    def test_preload_logs_which_explicit_overrides_are_kept(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        loader = _loader(tmp_path)
        loader["globals"] = {"g": "override"}
        loader["credentials"] = {"token": "override"}

        with caplog.at_level("INFO", logger="kedro.config.lazy_omegaconf_config"):
            loader.preload()

        assert "'credentials', 'globals'" in caplog.text
        assert "they override values from configuration files" in caplog.text

    def test_preload_without_overrides_does_not_log(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("INFO", logger="kedro.config.lazy_omegaconf_config"):
            _loader(tmp_path).preload()

        assert not caplog.records

    def test_unresolved_config_is_read_only_and_keeps_interpolations(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${runtime_params:value,1}"},
        )
        config = _loader(tmp_path).get_unresolved_config("parameters")

        assert OmegaConf.to_container(config, resolve=False) == {
            "value": "${runtime_params:value,1}"
        }
        with pytest.raises(ReadonlyConfigError):
            config.value = 2

    def test_unresolved_config_explicit_override_must_be_a_mapping(
        self, tmp_path: Path
    ) -> None:
        loader = _loader(tmp_path)
        loader["parameters"] = [1, 2]

        with pytest.raises(TypeError, match="mapping values"):
            loader.get_unresolved_config("parameters")
