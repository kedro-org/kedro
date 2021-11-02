import pytest

from kedro.framework.hooks.manager import _create_hook_manager
from kedro.framework.hooks.specs import DataCatalogSpecs, NodeSpecs, PipelineSpecs


@pytest.mark.parametrize(
    "hook_specs,hook_name,hook_params",
    [
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
                "run_id",
            ),
        ),
        (
            NodeSpecs,
            "before_node_run",
            ("node", "catalog", "inputs", "is_async", "run_id"),
        ),
        (
            NodeSpecs,
            "after_node_run",
            ("node", "catalog", "inputs", "outputs", "is_async", "run_id"),
        ),
        (
            NodeSpecs,
            "on_node_error",
            ("error", "node", "catalog", "inputs", "is_async", "run_id"),
        ),
        (PipelineSpecs, "before_pipeline_run", ("run_params", "pipeline", "catalog")),
        (PipelineSpecs, "after_pipeline_run", ("run_params", "pipeline", "catalog")),
        (
            PipelineSpecs,
            "on_pipeline_error",
            ("error", "run_params", "pipeline", "catalog"),
        ),
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
