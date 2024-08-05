import pytest

from kedro.framework.cli.hooks.manager import CLIHooksManager
from kedro.framework.cli.hooks.specs import CLICommandSpecs


@pytest.mark.parametrize(
    "hook_specs,hook_name,hook_params",
    [(CLICommandSpecs, "after_command_run", ("project_metadata", "command_args"))],
)
def test_hook_manager_can_call_hooks_defined_in_specs(
    hook_specs, hook_name, hook_params
):
    """Tests to make sure that the hook manager can call all hooks defined by specs."""
    cli_hook_manager = CLIHooksManager()
    hook = getattr(cli_hook_manager.hook, hook_name)
    assert hook.spec.namespace == hook_specs
    kwargs = {param: None for param in hook_params}
    result = hook(**kwargs)
    # since there hasn't been any hook implementation, the result should be empty
    # but it shouldn't have raised
    assert result == []
