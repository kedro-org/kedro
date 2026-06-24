import inspect
import re
from pathlib import Path

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
                "parameters",
                "save_version",
                "load_versions",
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


def test_hook_args_doc_table_matches_specs():
    """Guards the per-hook argument table in docs/extend/hooks/introduction.md
    against drift from the actual hook spec signatures (issue #4564).

    The intro page advertises which arguments each hook receives so users can
    pick the subset they need (pluggy's opt-in arguments). If a spec gains or
    loses an argument and the table is not updated, this test fails. Update
    the table in docs/extend/hooks/introduction.md to match.
    """
    docs_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "extend"
        / "hooks"
        / "introduction.md"
    )
    text = docs_path.read_text(encoding="utf-8")

    # Locate the "Available arguments per hook" section and parse the markdown
    # table that follows it. The parser is intentionally narrow: it only matches
    # the rows whose first column is a backticked hook name, so prose around
    # the table is ignored.
    section = re.search(
        r"###\s+Available arguments per hook\s*\n(.*?)(?:\n##\s|\Z)",
        text,
        re.DOTALL,
    )
    assert section, (
        "Section '### Available arguments per hook' not found in "
        f"{docs_path}; the docs table guarded by this test was removed or "
        "renamed. Restore it or update this test."
    )

    documented: dict[str, tuple[str, ...]] = {}
    for row in re.finditer(
        r"^\|\s*`([a-z_]+)`\s*\|\s*([^|]+?)\s*\|", section.group(1), re.MULTILINE
    ):
        hook_name = row.group(1)
        args = tuple(
            a.strip().strip("`")
            for a in row.group(2).split(",")
            if a.strip().strip("`")
        )
        documented[hook_name] = args

    # Ground truth: parameter names declared on each spec method (minus `self`).
    spec_namespaces = (
        KedroContextSpecs,
        DataCatalogSpecs,
        PipelineSpecs,
        NodeSpecs,
        DatasetSpecs,
    )
    actual: dict[str, tuple[str, ...]] = {}
    for ns in spec_namespaces:
        for name, member in inspect.getmembers(ns, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            params = tuple(
                p for p in inspect.signature(member).parameters if p != "self"
            )
            actual[name] = params

    assert documented == actual, (
        "Hook argument table in docs/extend/hooks/introduction.md is out of "
        "sync with kedro.framework.hooks.specs. "
        f"documented={documented} actual={actual}"
    )


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
