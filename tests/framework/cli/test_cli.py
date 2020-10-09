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
from os.path import join
from pathlib import Path

import click
from mock import patch
from pytest import fixture, mark, raises, warns

from kedro import __version__ as version
from kedro.framework.cli import get_project_context
from kedro.framework.cli.cli import (
    _STARTER_ALIASES,
    _init_plugins,
    cli,
    load_entry_points,
)
from kedro.framework.cli.utils import (
    CommandCollection,
    KedroCliError,
    _clean_pycache,
    forward_command,
    get_pkg_version,
)


@click.group(name="stub_cli")
def stub_cli():
    """Stub CLI group description."""
    print("group callback")


@stub_cli.command(name="stub_command")
def stub_command():
    print("command callback")


@forward_command(stub_cli, name="forwarded_command")
def forwarded_command(args, **kwargs):  # pylint: disable=unused-argument
    print("fred", args)


@forward_command(stub_cli, name="forwarded_help", forward_help=True)
def forwarded_help(args, **kwargs):  # pylint: disable=unused-argument
    print("fred", args)


@forward_command(stub_cli)
def unnamed(args, **kwargs):  # pylint: disable=unused-argument
    print("fred", args)


@fixture
def invoke_result(cli_runner, request):
    cmd_collection = CommandCollection(("Commands", [cli, stub_cli]))
    return cli_runner.invoke(cmd_collection, request.param)


@fixture
def requirements_file(tmp_path):
    body = "\n".join(["SQLAlchemy>=1.2.0, <2.0", "pandas==0.23.0", "toposort"]) + "\n"
    reqs_file = tmp_path / "requirements.txt"
    reqs_file.write_text(body)
    yield reqs_file


# pylint:disable=too-few-public-methods
class DummyContext:
    def __init__(self):
        self.config_loader = "config_loader"

    catalog = "catalog"
    pipeline = "pipeline"
    project_name = "dummy_name"
    project_path = "dummy_path"
    project_version = "dummy_version"


@fixture
def mocked_load_context(mocker):
    return mocker.patch(
        "kedro.framework.cli.cli.load_context", return_value=DummyContext()
    )


class TestCliCommands:
    def test_cli(self, cli_runner):
        """Run `kedro` without arguments."""
        result = cli_runner.invoke(cli, [])

        assert result.exit_code == 0
        assert "kedro" in result.output

    def test_print_version(self, cli_runner):
        """Check that `kedro --version` and `kedro -V` outputs contain
        the current package version."""
        result = cli_runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert version in result.output

        result_abr = cli_runner.invoke(cli, ["-V"])
        assert result_abr.exit_code == 0
        assert version in result_abr.output

    def test_info_contains_qb(self, cli_runner):
        """Check that `kedro info` output contains
        reference to QuantumBlack."""
        result = cli_runner.invoke(cli, ["info"])

        assert result.exit_code == 0
        assert "QuantumBlack" in result.output

    def test_info_contains_plugin_versions(self, cli_runner, entry_point, mocker):
        get_distribution = mocker.patch("pkg_resources.get_distribution")
        get_distribution().version = "1.0.2"
        entry_point.module_name = "bob.fred"

        result = cli_runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "bob: 1.0.2 (hooks:global,init,line_magic,project)" in result.output

        entry_point.load.assert_not_called()

    @mark.usefixtures("entry_points")
    def test_info_no_plugins(self, cli_runner):
        result = cli_runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "No plugins installed" in result.output

    def test_help(self, cli_runner):
        """Check that `kedro --help` returns a valid help message."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "kedro" in result.output

        result = cli_runner.invoke(cli, ["-h"])
        assert result.exit_code == 0
        assert "-h, --help     Show this message and exit." in result.output

    @patch("webbrowser.open")
    def test_docs(self, patched_browser, cli_runner):
        """Check that `kedro docs` opens a correct file in the browser."""
        result = cli_runner.invoke(cli, ["docs"])

        assert result.exit_code == 0
        for each in ("Opening file", join("html", "index.html")):
            assert each in result.output

        assert patched_browser.call_count == 1
        args, _ = patched_browser.call_args
        for each in ("file://", join("kedro", "framework", "html", "index.html")):
            assert each in args[0]

    def test_starter_list(self, cli_runner):
        """Check that `kedro starter list` prints out all starter aliases."""
        result = cli_runner.invoke(cli, ["starter", "list"])

        assert result.exit_code == 0, result.output
        for alias in _STARTER_ALIASES:
            assert alias in result.output


class TestCommandCollection:
    @mark.parametrize("invoke_result", [["stub_command"]], indirect=True)
    def test_found(self, invoke_result):
        """Test calling existing command."""
        assert invoke_result.exit_code == 0
        assert "group callback" not in invoke_result.output
        assert "command callback" in invoke_result.output

    def test_found_reverse(self, cli_runner):
        """Test calling existing command."""
        cmd_collection = CommandCollection(("Commands", [stub_cli, cli]))
        invoke_result = cli_runner.invoke(cmd_collection, ["stub_command"])
        assert invoke_result.exit_code == 0
        assert "group callback" in invoke_result.output
        assert "command callback" in invoke_result.output

    @mark.parametrize("invoke_result", [["not_found"]], indirect=True)
    def test_not_found(self, invoke_result):
        """Test calling nonexistent command."""
        assert invoke_result.exit_code == 2
        assert "No such command" in invoke_result.output
        assert "Did you mean one of these" not in invoke_result.output

    def test_not_found_closest_match(self, cli_runner, mocker):
        """Check that calling a nonexistent command with a close match returns the close match"""
        patched_difflib = mocker.patch(
            "kedro.framework.cli.utils.difflib.get_close_matches",
            return_value=["suggestion_1", "suggestion_2"],
        )

        cmd_collection = CommandCollection(("Commands", [stub_cli, cli]))
        invoke_result = cli_runner.invoke(cmd_collection, ["not_found"])

        patched_difflib.assert_called_once_with(
            "not_found", mocker.ANY, mocker.ANY, mocker.ANY
        )

        assert invoke_result.exit_code == 2
        assert "No such command" in invoke_result.output
        assert "Did you mean one of these?" in invoke_result.output
        assert "suggestion_1" in invoke_result.output
        assert "suggestion_2" in invoke_result.output

    def test_not_found_closet_match_singular(self, cli_runner, mocker):
        """Check that calling a nonexistent command with a close match has the proper wording"""
        patched_difflib = mocker.patch(
            "kedro.framework.cli.utils.difflib.get_close_matches",
            return_value=["suggestion_1"],
        )

        cmd_collection = CommandCollection(("Commands", [stub_cli, cli]))
        invoke_result = cli_runner.invoke(cmd_collection, ["not_found"])

        patched_difflib.assert_called_once_with(
            "not_found", mocker.ANY, mocker.ANY, mocker.ANY
        )

        assert invoke_result.exit_code == 2
        assert "No such command" in invoke_result.output
        assert "Did you mean this?" in invoke_result.output
        assert "suggestion_1" in invoke_result.output

    @mark.parametrize("invoke_result", [[]], indirect=True)
    def test_help(self, invoke_result):
        """Check that help output includes stub_cli group description."""
        assert invoke_result.exit_code == 0
        assert "Stub CLI group description" in invoke_result.output
        assert "Kedro is a CLI" in invoke_result.output


class TestForwardCommand:
    def test_regular(self, cli_runner):
        """Test forwarded command invocation."""
        result = cli_runner.invoke(stub_cli, ["forwarded_command", "bob"])
        assert result.exit_code == 0, result.output
        assert "bob" in result.output
        assert "fred" in result.output
        assert "--help" not in result.output
        assert "forwarded_command" not in result.output

    def test_unnamed(self, cli_runner):
        """Test forwarded command invocation."""
        result = cli_runner.invoke(stub_cli, ["unnamed", "bob"])
        assert result.exit_code == 0, result.output
        assert "bob" in result.output
        assert "fred" in result.output
        assert "--help" not in result.output
        assert "forwarded_command" not in result.output

    def test_help(self, cli_runner):
        """Test help output for the command with help flags not forwarded."""
        result = cli_runner.invoke(stub_cli, ["forwarded_command", "bob", "--help"])
        assert result.exit_code == 0, result.output
        assert "bob" not in result.output
        assert "fred" not in result.output
        assert "--help" in result.output
        assert "forwarded_command" in result.output

    def test_forwarded_help(self, cli_runner):
        """Test help output for the command with forwarded help flags."""
        result = cli_runner.invoke(stub_cli, ["forwarded_help", "bob", "--help"])
        assert result.exit_code == 0, result.output
        assert "bob" in result.output
        assert "fred" in result.output
        assert "--help" in result.output
        assert "forwarded_help" not in result.output


class TestCliUtils:
    def test_get_pkg_version(self, requirements_file):
        """Test get_pkg_version(), which extracts package version
        from the provided requirements file."""
        sa_version = "SQLAlchemy>=1.2.0, <2.0"
        assert get_pkg_version(requirements_file, "SQLAlchemy") == sa_version
        assert get_pkg_version(requirements_file, "pandas") == "pandas==0.23.0"
        assert get_pkg_version(requirements_file, "toposort") == "toposort"
        with raises(KedroCliError):
            get_pkg_version(requirements_file, "nonexistent")
        with raises(KedroCliError):
            non_existent_file = str(requirements_file) + "-nonexistent"
            get_pkg_version(non_existent_file, "pandas")

    def test_clean_pycache(self, tmp_path, mocker):
        """Test `clean_pycache` utility function"""
        source = Path(tmp_path)
        pycache2 = Path(source / "nested1" / "nested2" / "__pycache__").resolve()
        pycache2.mkdir(parents=True)
        pycache1 = Path(source / "nested1" / "__pycache__").resolve()
        pycache1.mkdir()
        pycache = Path(source / "__pycache__").resolve()
        pycache.mkdir()

        mocked_rmtree = mocker.patch("shutil.rmtree")
        _clean_pycache(source)

        expected_calls = [
            mocker.call(pycache, ignore_errors=True),
            mocker.call(pycache1, ignore_errors=True),
            mocker.call(pycache2, ignore_errors=True),
        ]
        assert mocked_rmtree.mock_calls == expected_calls


@mark.usefixtures("mocked_load_context")
class TestGetProjectContext:
    def _deprecation_msg(self, key):
        msg_dict = {
            "get_config": ["config_loader", "ConfigLoader"],
            "create_catalog": ["catalog", "DataCatalog"],
            "create_pipeline": ["pipeline", "Pipeline"],
            "template_version": ["project_version", None],
            "project_name": ["project_name", None],
            "project_path": ["project_path", None],
        }
        attr, obj_name = msg_dict[key]
        msg = r"\`get_project_context\(\"{}\"\)\` is now deprecated\. ".format(key)
        if obj_name:
            msg += (
                r"This is still returning a function that returns \`{}\` "
                r"instance\, however passed arguments have no effect anymore "
                r"since Kedro 0.15.0\. ".format(obj_name)
            )
        msg += (
            r"Please get \`KedroContext\` instance by calling "
            r"\`get_project_context\(\)\` and use its \`{}\` attribute\.".format(attr)
        )
        return msg

    def test_get_context_without_project_path(self, mocked_load_context):
        dummy_context = get_project_context("context")
        mocked_load_context.assert_called_once_with(Path.cwd())
        assert isinstance(dummy_context, DummyContext)

    def test_get_context_with_project_path(self, tmpdir, mocked_load_context):
        dummy_project_path = tmpdir.mkdir("dummy_project")
        dummy_context = get_project_context("context", project_path=dummy_project_path)
        mocked_load_context.assert_called_once_with(dummy_project_path)
        assert isinstance(dummy_context, DummyContext)

    def test_get_config(self, tmp_path):
        key = "get_config"
        pattern = self._deprecation_msg(key)
        with warns(DeprecationWarning, match=pattern):
            config_loader = get_project_context(key)
            assert config_loader(tmp_path) == "config_loader"

    def test_create_catalog(self):
        key = "create_catalog"
        pattern = self._deprecation_msg(key)
        with warns(DeprecationWarning, match=pattern):
            catalog = get_project_context(key)
            assert catalog("config") == "catalog"

    def test_create_pipeline(self):
        key = "create_pipeline"
        pattern = self._deprecation_msg(key)
        with warns(DeprecationWarning, match=pattern):
            pipeline = get_project_context(key)
            assert pipeline() == "pipeline"

    def test_template_version(self):
        key = "template_version"
        pattern = self._deprecation_msg(key)
        with warns(DeprecationWarning, match=pattern):
            assert get_project_context(key) == "dummy_version"

    def test_project_name(self):
        key = "project_name"
        pattern = self._deprecation_msg(key)
        with warns(DeprecationWarning, match=pattern):
            assert get_project_context(key) == "dummy_name"

    def test_project_path(self):
        key = "project_path"
        pattern = self._deprecation_msg(key)
        with warns(DeprecationWarning, match=pattern):
            assert get_project_context(key) == "dummy_path"

    def test_verbose(self):
        assert not get_project_context("verbose")


class TestEntryPoints:
    def test_project_groups(self, entry_points, entry_point):
        entry_point.load.return_value = "groups"
        groups = load_entry_points("project")
        assert groups == ["groups"]
        entry_points.assert_called_once_with(group="kedro.project_commands")

    def test_project_error_is_caught(self, entry_points, entry_point):
        entry_point.load.side_effect = Exception()
        with raises(KedroCliError, match="Loading project commands"):
            load_entry_points("project")

        entry_points.assert_called_once_with(group="kedro.project_commands")

    def test_global_groups(self, entry_points, entry_point):
        entry_point.load.return_value = "groups"
        groups = load_entry_points("global")
        assert groups == ["groups"]
        entry_points.assert_called_once_with(group="kedro.global_commands")

    def test_global_error_is_caught(self, entry_points, entry_point):
        entry_point.load.side_effect = Exception()
        with raises(KedroCliError, match="Loading global commands from"):
            load_entry_points("global")
        entry_points.assert_called_once_with(group="kedro.global_commands")

    def test_init(self, entry_points, entry_point):
        _init_plugins()
        entry_points.assert_called_once_with(group="kedro.init")
        entry_point.load().assert_called_once_with()

    def test_init_error_is_caught(self, entry_points, entry_point):
        entry_point.load.side_effect = Exception()
        with raises(KedroCliError, match="Initializing"):
            _init_plugins()
        entry_points.assert_called_once_with(group="kedro.init")
