from __future__ import annotations

import threading
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

if TYPE_CHECKING:
    from pathlib import Path


def _write_yaml(filepath: Path, config: dict[str, Any]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(yaml.safe_dump(config))


def _loader(
    root: Path,
    interpolation_scope: str = "merged",
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
    def test_loader_is_marked_experimental(self) -> None:
        assert LazyOmegaConfigLoader.__kedro_experimental__ is True
        assert LazyOmegaConfigLoader.__doc__.startswith('!!! warning "Experimental"')

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
        register = mocker.spy(OmegaConf, "register_new_resolver")
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

    def test_interpolation_scope_merged_resolves_after_environment_merge(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"param1": "${param2}", "param2": "base"},
        )
        _write_yaml(tmp_path / "local" / "parameters.yml", {"param2": "local"})

        assert _loader(tmp_path)["parameters"] == {
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
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${oc.env:LAZY_CUSTOM}"},
        )
        original_resolver = OmegaConf._get_resolver("oc.env")

        def previous_resolver(variable: str) -> str:
            return "previous-value"

        OmegaConf.register_new_resolver("oc.env", previous_resolver, replace=True)
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

    def test_runtime_params_are_not_supported_in_globals(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base" / "globals.yml",
            {"value": "${runtime_params:value}"},
        )
        loader = _loader(tmp_path)

        with pytest.raises(
            UnsupportedInterpolationType, match="not supported for globals"
        ):
            loader["globals"]

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

    def test_concurrent_run_views_do_not_cross_contaminate(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${runtime_params:value}"},
        )
        loader = _loader(tmp_path)
        loader.preload()

        def resolve(value: int) -> bool:
            view = loader.with_runtime_params({"value": value})
            return view["parameters"]["value"] == value

        with ThreadPoolExecutor(max_workers=8) as executor:
            assert all(executor.map(resolve, range(80)))

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

    def test_unresolved_config_is_read_only_and_keeps_interpolations(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base" / "parameters.yml",
            {"value": "${runtime_params:value,1}"},
        )
        config = _loader(tmp_path)._get_unresolved_config("parameters")

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
            loader._get_unresolved_config("parameters")
