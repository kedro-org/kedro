from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from kedro.framework.project import _callable_supports_selective, _ProjectPipelines

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class _CallSpy:
    fn: Callable[..., dict[str, object]]

    def __post_init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.__wrapped__ = self.fn

    def __call__(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append((args, kwargs))
        return self.fn(*args, **kwargs)


@pytest.fixture
def project_pipelines() -> _ProjectPipelines:
    pipelines = _ProjectPipelines()
    pipelines.configure("package.pipeline_registry")
    return pipelines


def _selective_registry(
    pipelines_to_find: list[str] | None = None,
) -> dict[str, object]:
    pipelines = {
        "__default__": object(),
        "alpha": object(),
        "beta": object(),
    }
    if pipelines_to_find is None:
        return pipelines
    return {name: pipelines[name] for name in pipelines_to_find if name in pipelines}


def _legacy_registry() -> dict[str, object]:
    return {"__default__": object(), "alpha": object(), "beta": object()}


def test_callable_supports_selective_real_function() -> None:
    assert _callable_supports_selective(_selective_registry)


def test_callable_supports_selective_inspect_unwrap_error_returns_false(mocker) -> None:
    mocker.patch("kedro.framework.project.inspect.unwrap", side_effect=ValueError)

    assert not _callable_supports_selective(_selective_registry)


def test_selective_getitem_loads_requested_key_and_caches_it(
    mocker, project_pipelines
) -> None:
    registry = _CallSpy(_selective_registry)
    get_registry = mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )

    first_result = project_pipelines["alpha"]
    second_result = project_pipelines["alpha"]

    assert first_result is second_result
    assert first_result is not None
    assert registry.calls == [
        (
            (),
            {"pipelines_to_find": ["alpha"]},
        )
    ]
    get_registry.assert_called_once_with("package.pipeline_registry")


def test_selective_getitem_loads_another_key_without_full_reload(
    mocker, project_pipelines
) -> None:
    registry = _CallSpy(_selective_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )

    project_pipelines["alpha"]
    project_pipelines["beta"]

    assert registry.calls == [
        ((), {"pipelines_to_find": ["alpha"]}),
        ((), {"pipelines_to_find": ["beta"]}),
    ]


def test_full_load_operations_force_complete_registry_load(
    mocker, project_pipelines
) -> None:
    registry = _CallSpy(_selective_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )

    project_pipelines["alpha"]

    operations = [
        list,
        len,
        lambda mapping: list(mapping.keys()),
        lambda mapping: list(mapping.values()),
        lambda mapping: list(mapping.items()),
        repr,
        str,
    ]

    for operation in operations:
        result = operation(project_pipelines)
        assert result is not None

    assert registry.calls[0] == ((), {"pipelines_to_find": ["alpha"]})
    assert registry.calls[1] == ((), {})


def test_legacy_registry_falls_back_to_full_load(mocker, project_pipelines) -> None:
    registry = _CallSpy(_legacy_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )

    result = project_pipelines["alpha"]

    assert result is not None
    assert registry.calls == [((), {})]


def test_configure_clears_partial_cache(mocker, project_pipelines) -> None:
    registry = _CallSpy(_selective_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )

    first_alpha = project_pipelines["alpha"]
    project_pipelines.configure("package.pipeline_registry")
    second_registry = _CallSpy(_selective_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=second_registry,
    )

    second_alpha = project_pipelines["alpha"]

    assert first_alpha is not None
    assert second_alpha is not None
    assert registry.calls == [((), {"pipelines_to_find": ["alpha"]})]
    assert second_registry.calls == [((), {"pipelines_to_find": ["alpha"]})]


def test_selective_path_falls_back_when_helper_returns_false(
    mocker, project_pipelines
) -> None:
    registry = _CallSpy(_selective_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )
    mocker.patch(
        "kedro.framework.project._callable_supports_selective",
        return_value=False,
    )

    project_pipelines["alpha"]

    assert registry.calls == [((), {})]


def test_setitem_and_delitem_force_full_load(mocker, project_pipelines) -> None:
    registry = _CallSpy(_selective_registry)
    mocker.patch.object(
        project_pipelines,
        "_get_pipelines_registry_callable",
        return_value=registry,
    )

    project_pipelines["gamma"] = object()
    project_pipelines["gamma"]
    del project_pipelines["gamma"]

    assert registry.calls == [((), {})]
    assert "gamma" not in project_pipelines._content
