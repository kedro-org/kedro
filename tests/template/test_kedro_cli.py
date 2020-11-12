# Copyright 2020 QuantumBlack Visual Analytics Limited
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
# pylint: disable=unused-argument

from pathlib import Path

import anyconfig
import pytest
from click.testing import CliRunner

from kedro.framework.session import KedroSession
from kedro.runner import ParallelRunner, SequentialRunner


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestRunCommand:
    @staticmethod
    @pytest.fixture(autouse=True)
    def mocked_session_manager(mocker):
        mock_session_create = mocker.patch.object(KedroSession, "create")
        mock_load_context = (
            mock_session_create.return_value.__enter__.return_value.load_context
        )
        # needed to be able to print the parameters in test_starter/.../cli.py
        mock_load_context.return_value.params = {"fake": True}
        return mock_session_create

    @staticmethod
    @pytest.fixture(params=["run_config.yml", "run_config.json"])
    def fake_run_config(request, fake_root_dir):
        config_path = str(fake_root_dir / request.param)
        anyconfig.dump(
            {
                "run": {
                    "pipeline": "pipeline1",
                    "tag": ["tag1", "tag2"],
                    "node_names": ["node1", "node2"],
                }
            },
            config_path,
        )
        return config_path

    @staticmethod
    @pytest.fixture()
    def fake_run_config_with_params(fake_run_config, request):
        config = anyconfig.load(fake_run_config)
        config["run"].update(request.param)
        anyconfig.dump(config, fake_run_config)
        return fake_run_config

    def test_run_successfully(self, fake_project_cli, mocked_session_manager, mocker):
        result = CliRunner().invoke(fake_project_cli.cli, ["run"])
        assert not result.exit_code

        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        mocked_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={},
            pipeline_name=None,
        )

        runner = mocked_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    def test_with_sequential_runner_and_parallel_flag(
        self, fake_project_cli, mocked_session_manager
    ):
        result = CliRunner().invoke(
            fake_project_cli.cli, ["run", "--parallel", "--runner=SequentialRunner"]
        )
        assert result.exit_code
        assert "Please use either --parallel or --runner" in result.stdout

        mocked_session_manager.return_value.run.assert_not_called()

    def test_run_successfully_parallel_via_flag(
        self, fake_project_cli, mocked_session_manager, mocker
    ):
        result = CliRunner().invoke(fake_project_cli.cli, ["run", "--parallel"])
        assert not result.exit_code
        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        mocked_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={},
            pipeline_name=None,
        )

        runner = mocked_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, ParallelRunner)
        assert not runner._is_async

    def test_run_successfully_parallel_via_name(
        self, fake_project_cli, mocked_session_manager
    ):
        result = CliRunner().invoke(
            fake_project_cli.cli, ["run", "--runner=ParallelRunner"]
        )
        assert not result.exit_code
        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        runner = mocked_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, ParallelRunner)
        assert not runner._is_async

    def test_run_async(self, fake_project_cli, mocked_session_manager, mocker):
        result = CliRunner().invoke(fake_project_cli.cli, ["run", "--async"])
        assert not result.exit_code
        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        runner = mocked_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert runner._is_async

    @pytest.mark.parametrize("config_flag", ["--config", "-c"])
    def test_run_with_config(
        self,
        config_flag,
        fake_project_cli,
        mocked_session_manager,
        fake_run_config,
        mocker,
    ):
        result = CliRunner().invoke(
            fake_project_cli.cli, ["run", config_flag, fake_run_config]
        )
        assert not result.exit_code
        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        mocked_session.run.assert_called_once_with(
            tags=("tag1", "tag2"),
            runner=mocker.ANY,
            node_names=("node1", "node2"),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={},
            pipeline_name="pipeline1",
        )

    @pytest.mark.parametrize(
        "fake_run_config_with_params,expected",
        [
            ({}, {}),
            ({"params": {"foo": "baz"}}, {"foo": "baz"}),
            ({"params": "foo:baz"}, {"foo": "baz"}),
            (
                {"params": {"foo": "123.45", "baz": "678", "bar": 9}},
                {"foo": "123.45", "baz": "678", "bar": 9},
            ),
        ],
        indirect=["fake_run_config_with_params"],
    )
    def test_run_with_params_in_config(
        self,
        expected,
        fake_project_cli,
        mocked_session_manager,
        fake_run_config_with_params,
        mocker,
    ):
        result = CliRunner().invoke(
            fake_project_cli.cli, ["run", "-c", fake_run_config_with_params]
        )

        assert not result.exit_code
        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        mocked_session.run.assert_called_once_with(
            tags=("tag1", "tag2"),
            runner=mocker.ANY,
            node_names=("node1", "node2"),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={},
            pipeline_name="pipeline1",
        )
        mocked_session_manager.assert_called_once_with(
            project_path=Path.cwd(), env=mocker.ANY, extra_params=expected
        )

    @pytest.mark.parametrize(
        "cli_arg,expected_extra_params",
        [
            ("foo:bar", {"foo": "bar"}),
            (
                "foo:123.45, bar:1a,baz:678. ,qux:1e-2,quux:0,quuz:",
                {
                    "foo": 123.45,
                    "bar": "1a",
                    "baz": 678,
                    "qux": 0.01,
                    "quux": 0,
                    "quuz": "",
                },
            ),
            ("foo:bar,baz:fizz:buzz", {"foo": "bar", "baz": "fizz:buzz"}),
            (
                "foo:bar, baz: https://example.com",
                {"foo": "bar", "baz": "https://example.com"},
            ),
            ("foo:bar,baz:fizz buzz", {"foo": "bar", "baz": "fizz buzz"}),
            ("foo:bar, foo : fizz buzz  ", {"foo": "fizz buzz"}),
        ],
    )
    def test_run_extra_params(
        self,
        mocker,
        fake_project_cli,
        mocked_session_manager,
        cli_arg,
        expected_extra_params,
    ):
        result = CliRunner().invoke(fake_project_cli.cli, ["run", "--params", cli_arg])

        assert not result.exit_code
        mocked_session_manager.assert_called_once_with(
            project_path=Path.cwd(), env=mocker.ANY, extra_params=expected_extra_params
        )

    @pytest.mark.parametrize("bad_arg", ["bad", "foo:bar,bad"])
    def test_bad_extra_params(self, fake_project_cli, bad_arg):
        result = CliRunner().invoke(fake_project_cli.cli, ["run", "--params", bad_arg])
        assert result.exit_code
        assert (
            "Item `bad` must contain a key and a value separated by `:`"
            in result.stdout
        )

    @pytest.mark.parametrize("bad_arg", [":", ":value", " :value"])
    def test_bad_params_key(self, fake_project_cli, bad_arg):
        result = CliRunner().invoke(fake_project_cli.cli, ["run", "--params", bad_arg])
        assert result.exit_code
        assert "Parameter key cannot be an empty string" in result.stdout

    @pytest.mark.parametrize(
        "option,value",
        [("--load-version", "dataset1:time1"), ("-lv", "dataset2:time2")],
    )
    def test_reformat_load_versions(
        self, fake_project_cli, mocked_session_manager, option, value, mocker
    ):
        result = CliRunner().invoke(fake_project_cli.cli, ["run", option, value])
        assert not result.exit_code, result.output

        ds, t = value.split(":", 1)
        mocked_session = mocked_session_manager.return_value.__enter__.return_value
        mocked_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={ds: t},
            pipeline_name=None,
        )

    def test_fail_reformat_load_versions(self, fake_project_cli):
        load_version = "2020-05-12T12.00.00"
        result = CliRunner().invoke(fake_project_cli.cli, ["run", "-lv", load_version])
        assert result.exit_code, result.output

        expected_output = (
            f"Error: Expected the form of `load_version` to be "
            f"`dataset_name:YYYY-MM-DDThh.mm.ss.sssZ`,"
            f"found {load_version} instead\n"
        )
        assert expected_output in result.output
