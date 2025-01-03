import pytest
from pluggy import PluginManager

from kedro.framework.hooks.manager import (
    _create_hook_manager,
    _NullPluginManager,
    _register_hooks,
)
from kedro.framework.hooks.specs import (
    DataCatalogSpecs,
    DatasetSpecs,
    KedroContextSpecs,
    NodeSpecs,
    PipelineSpecs,
)


class ExampleHook:
    pass


@pytest.mark.parametrize(
    "hook_specs,hook_name,hook_params",
    [
        (KedroContextSpecs, "after_context_created", ("context")),
        (
            DataCatalogSpecs,
            "after_catalog_created",
            (
                "catalog",
                "conf_catalog",
                "conf_creds",
                "feed_dict",
                "save_version",
                "load_versions",
            ),
        ),
        (
            NodeSpecs,
            "before_node_run",
            ("node", "catalog", "inputs", "is_async", "session_id"),
        ),
        (
            NodeSpecs,
            "after_node_run",
            ("node", "catalog", "inputs", "outputs", "is_async", "session_id"),
        ),
        (
            NodeSpecs,
            "on_node_error",
            ("error", "node", "catalog", "inputs", "is_async", "session_id"),
        ),
        (PipelineSpecs, "before_pipeline_run", ("run_params", "pipeline", "catalog")),
        (PipelineSpecs, "after_pipeline_run", ("run_params", "pipeline", "catalog")),
        (
            PipelineSpecs,
            "on_pipeline_error",
            ("error", "run_params", "pipeline", "catalog"),
        ),
        (DatasetSpecs, "before_dataset_loaded", ("dataset_name")),
        (DatasetSpecs, "after_dataset_loaded", ("dataset_name", "data")),
        (DatasetSpecs, "before_dataset_saved", ("dataset_name", "data")),
        (DatasetSpecs, "after_dataset_saved", ("dataset_name", "data")),
    ],
)
def test_hook_manager_can_call_hooks_defined_in_specs(
    hook_specs, hook_name, hook_params
):
    """Tests to make sure that the hook manager can call all hooks defined by specs."""
    hook_manager = _create_hook_manager()
    hook = getattr(hook_manager.hook, hook_name)
    assert hook.spec.namespace == hook_specs
    kwargs = {param: None for param in hook_params}
    result = hook(**kwargs)
    # since there hasn't been any hook implementation, the result should be empty
    # but it shouldn't have raised
    assert result == []


def test_null_plugin_manager_returns_none_when_called():
    plugin_manager = _NullPluginManager()
    assert (
        plugin_manager.hook.before_dataset_saved(dataset_name="mock", data=[]) is None
    )


@pytest.mark.parametrize(
    "hooks, should_raise",
    [
        ([ExampleHook], True),
        ([ExampleHook()], False),
    ],
)
def test_register_hooks(hooks, should_raise):
    mock_hook_manager = PluginManager("test_project")

    if should_raise:
        with pytest.raises(
            TypeError, match="KedroSession expects hooks to be registered as instances"
        ):
            _register_hooks(mock_hook_manager, hooks)
    else:
        _register_hooks(mock_hook_manager, hooks)
        assert mock_hook_manager.is_registered(hooks[0])
