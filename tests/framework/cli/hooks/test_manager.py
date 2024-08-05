import pytest

from kedro.framework.cli.hooks.manager import CLIHooksManager
from kedro.framework.cli.hooks.specs import CLICommandSpecs


@pytest.mark.parametrize(
    "hook_specs,hook_name",
    [(CLICommandSpecs, "before_command_run")],
)
def test_hook_manager_can_call_hooks_defined_in_specs(hook_specs, hook_name):
    """Tests to make sure that the hook manager can call all hooks defined by specs."""
    cli_hook_manager = CLIHooksManager()
    hook = getattr(cli_hook_manager.hook, hook_name)
    assert hook.spec.namespace == hook_specs
    # kedro-telemetry installed by default, this test runs the telemetry before_command_run hook, which
    # is expecting the command_args to be a list version of the command like ['kedro', 'run']
    kwargs = {"command_args": ["kedro", "run"], "project_metadata": None}
    result = hook(**kwargs)
    assert result == []
