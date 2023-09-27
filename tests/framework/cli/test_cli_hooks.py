from __future__ import annotations

import logging
from collections import namedtuple

import pytest
from click.testing import CliRunner

from kedro.framework.cli.cli import KedroCLI, cli
from kedro.framework.cli.hooks import cli_hook_impl, get_cli_hook_manager, manager
from kedro.framework.startup import ProjectMetadata

logger = logging.getLogger(__name__)

FakeDistribution = namedtuple(
    "FakeDistribution", ["entry_points", "metadata", "version"]
)


@pytest.fixture(autouse=True)
def reset_hook_manager():
    """Due to singleton nature of the `_cli_hook_manager`, the `_cli_hook_manager`
    must be reset to `None` so that a new `CLIHookManager` gets created at the point
    where `FakeEntryPoint` and `fake_plugin_distribution` exist within the same scope.
    Additionally, this prevents `CLIHookManager` to be set from scope outside of this
    testing module.
    """
    manager._cli_hook_manager = None
    yield
    hook_manager = get_cli_hook_manager()
    plugins = hook_manager.get_plugins()
    for plugin in plugins:
        hook_manager.unregister(plugin)


class FakeEntryPoint:
    name = "fake-plugin"
    group = "kedro.cli_hooks"
    value = "hooks:cli_hooks"

    def load(self):
        class FakeCLIHooks:
            @cli_hook_impl
            def before_command_run(
                self,
                project_metadata: ProjectMetadata,
                command_args: list[str],
            ):
                print(
                    f"Before command `{' '.join(command_args)}` run for project {project_metadata}"
                )

            @cli_hook_impl
            def after_command_run(
                self,
                project_metadata: ProjectMetadata,
                command_args: list[str],
                exit_code: int,
            ):
                print(
                    f"After command `{' '.join(command_args)}` run for project {project_metadata} "
                    f"(exit: {exit_code})"
                )

        return FakeCLIHooks()


@pytest.fixture
def fake_plugin_distribution(mocker):
    fake_entrypoint = FakeEntryPoint()
    fake_distribution = FakeDistribution(
        entry_points=(fake_entrypoint,),
        metadata={"name": fake_entrypoint.name},
        version="0.1",
    )
    mocker.patch(
        "pluggy._manager.importlib.metadata.distributions",
        return_value=[fake_distribution],
    )
    return fake_distribution


class TestKedroCLIHooks:
    @pytest.mark.parametrize(
        "command, exit_code",
        [("-V", 0), ("info", 2), ("pipeline list", 2), ("starter", 0)],
    )
    def test_kedro_cli_should_invoke_cli_hooks_from_plugin(
        self,
        caplog,
        command,
        exit_code,
        mocker,
        fake_metadata,
        fake_plugin_distribution,
        entry_points,
    ):
        caplog.set_level(logging.DEBUG, logger="kedro")

        Module = namedtuple("Module", ["cli"])
        mocker.patch(
            "kedro.framework.cli.cli._is_project",
            return_value=True,
        )
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project",
            return_value=fake_metadata,
        )
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module",
            return_value=Module(cli=cli),
        )
        kedro_cli = KedroCLI(fake_metadata.project_path)
        result = CliRunner().invoke(kedro_cli, [command])
        assert (
            f"Registered CLI hooks from 1 installed plugin(s): "
            f"{fake_plugin_distribution.metadata['name']}-{fake_plugin_distribution.version}"
            in caplog.text
        )
        assert (
            f"Before command `{command}` run for project {fake_metadata}"
            in result.output
        )

        # 'pipeline list' and 'info' aren't actually in the click structure and
        # return exit code 2 ('invalid usage of some shell built-in command')
        assert (
            f"After command `{command}` run for project {fake_metadata} (exit: {exit_code})"
        ) in result.output
