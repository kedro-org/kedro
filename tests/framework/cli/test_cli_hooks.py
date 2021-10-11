# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from collections import namedtuple
from typing import List

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
                command_args: List[str],
            ):
                print(
                    f"Before command `{' '.join(command_args)}` run for project {project_metadata}"
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
        "pluggy.manager.importlib_metadata.distributions",
        return_value=[fake_distribution],
    )
    return fake_distribution


class TestKedroCLIHooks:
    @pytest.mark.parametrize(
        "command",
        ["-V", "info", "pipeline list", "run --pipeline=test"],
    )
    def test_kedro_cli_should_invoke_cli_hooks_from_plugin(
        self,
        caplog,
        command,
        mocker,
        fake_metadata,
        fake_plugin_distribution,
    ):
        Module = namedtuple("Module", ["cli"])
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module",
            return_value=Module(cli=cli),
        )
        mocker.patch(
            "kedro.framework.cli.cli._is_project",
            return_value=True,
        )
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project",
            return_value=fake_metadata,
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
