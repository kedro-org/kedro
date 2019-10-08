# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=unused-argument
import os
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from click.testing import CliRunner

from kedro.runner import ParallelRunner, SequentialRunner


@pytest.fixture(autouse=True)
def call_mock(mocker, fake_kedro_cli):
    return mocker.patch.object(fake_kedro_cli, "call")


@pytest.fixture(autouse=True)
def python_call_mock(mocker, fake_kedro_cli):
    return mocker.patch.object(fake_kedro_cli, "python_call")


@pytest.fixture()
def fake_ipython_message(mocker, fake_kedro_cli):
    return mocker.patch.object(fake_kedro_cli, "ipython_message")


class TestActivateNbstripoutCommand:
    @staticmethod
    @pytest.fixture()
    def fake_nbstripout():
        """
        ``nbstripout`` tries to access ``sys.stdin.buffer.readable``
        on import, but it's patches by pytest.
        Let's replace it by the fake!
        """
        sys.modules["nbstripout"] = "fake"
        yield
        del sys.modules["nbstripout"]

    @staticmethod
    @pytest.fixture
    def missing_nbstripout(mocker):
        """
        Pretend ``nbstripout`` module doesn't exist.
        In fact, no new imports are possible after that.
        """
        sys.modules.pop("nbstripout", None)
        mocker.patch.object(sys, "path", [])

    @staticmethod
    @pytest.fixture
    def fake_git_repo(mocker):
        return mocker.patch("subprocess.run", return_value=mocker.Mock(returncode=0))

    @staticmethod
    @pytest.fixture
    def without_git_repo(mocker):
        return mocker.patch("subprocess.run", return_value=mocker.Mock(returncode=1))

    def test_install_successfully(
        self, fake_kedro_cli, call_mock, fake_nbstripout, fake_git_repo
    ):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["activate-nbstripout"])
        assert not result.exit_code

        call_mock.assert_called_once_with(["nbstripout", "--install"])

        fake_git_repo.assert_called_once_with(
            ["git", "rev-parse", "--git-dir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_nbstripout_not_found(
        self, fake_kedro_cli, missing_nbstripout, fake_git_repo
    ):
        """
        Run activate-nbstripout target without nbstripout installed
        There should be a clear message about it.
        """

        result = CliRunner().invoke(fake_kedro_cli.cli, ["activate-nbstripout"])
        assert result.exit_code
        assert "nbstripout is not installed" in result.stdout

    def test_no_git_repo(self, fake_kedro_cli, fake_nbstripout, without_git_repo):
        """
        Run activate-nbstripout target with no git repo available.
        There should be a clear message about it.
        """
        result = CliRunner().invoke(fake_kedro_cli.cli, ["activate-nbstripout"])

        assert result.exit_code
        assert "Not a git repository" in result.stdout


class TestRunCommand:
    @staticmethod
    @pytest.fixture(autouse=True)
    def fake_load_context(mocker, fake_kedro_cli):
        context = mocker.Mock()
        yield mocker.patch.object(fake_kedro_cli, "load_context", return_value=context)

    def test_run_successfully(self, fake_kedro_cli, fake_load_context, mocker):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["run"])
        assert not result.exit_code

        fake_load_context.return_value.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={},
            pipeline_name=None,
        )

        assert isinstance(
            fake_load_context.return_value.run.call_args_list[0][1]["runner"],
            SequentialRunner,
        )

    def test_with_sequential_runner_and_parallel_flag(
        self, fake_kedro_cli, fake_load_context
    ):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["run", "--parallel", "--runner=SequentialRunner"]
        )

        assert result.exit_code
        assert "Please use either --parallel or --runner" in result.stdout
        fake_load_context.return_value.run.assert_not_called()

    def test_run_successfully_parallel_via_flag(
        self, fake_kedro_cli, fake_load_context, mocker
    ):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["run", "--parallel"])

        assert not result.exit_code

        fake_load_context.return_value.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            load_versions={},
            pipeline_name=None,
        )

        assert isinstance(
            fake_load_context.return_value.run.call_args_list[0][1]["runner"],
            ParallelRunner,
        )

    def test_run_successfully_parallel_via_name(
        self, fake_kedro_cli, fake_load_context
    ):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["run", "--runner=ParallelRunner"]
        )

        assert not result.exit_code
        assert isinstance(
            fake_load_context.return_value.run.call_args_list[0][1]["runner"],
            ParallelRunner,
        )


class TestTestCommand:
    @staticmethod
    @pytest.fixture
    def missing_pytest(mocker):
        """
        Pretend ``nbstripout`` module doesn't exist.
        In fact, no new imports are possible after that.
        """
        sys.modules.pop("pytest", None)
        mocker.patch.object(sys, "path", [])

    def test_happy_path(self, fake_kedro_cli, python_call_mock):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["test", "--random-arg", "value"]
        )
        assert not result.exit_code
        python_call_mock.assert_called_once_with("pytest", ("--random-arg", "value"))

    def test_pytest_not_installed(
        self, fake_kedro_cli, python_call_mock, missing_pytest
    ):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["test", "--random-arg", "value"]
        )
        assert result.exit_code
        assert fake_kedro_cli.NO_PYTEST_MESSAGE in result.stdout
        python_call_mock.assert_not_called()


class TestInstallCommand:
    def test_happy_path(self, python_call_mock, call_mock, fake_kedro_cli):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["install"])
        assert not result.exit_code
        python_call_mock.assert_called_once_with(
            "pip", ["install", "-U", "-r", "src/requirements.txt"]
        )
        call_mock.assert_not_called()

    def test_with_env_file(self, python_call_mock, call_mock, fake_kedro_cli, mocker):
        # Pretend env file exists:
        mocker.patch.object(Path, "is_file", return_value=True)

        result = CliRunner().invoke(fake_kedro_cli.cli, ["install"])
        assert not result.exit_code, result.stdout
        python_call_mock.assert_called_once_with(
            "pip", ["install", "-U", "-r", "src/requirements.txt"]
        )
        call_mock.assert_called_once_with(
            ["conda", "install", "--file", "src/environment.yml", "--yes"]
        )


class TestIpythonCommand:
    def test_happy_path(self, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["ipython", "--random-arg", "value"]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with()
        call_mock.assert_called_once_with(["ipython", "--random-arg", "value"])

    @pytest.mark.parametrize("help_flag", ["-h", "--help"])
    def test_help(self, help_flag, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["ipython", help_flag])
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_not_called()
        call_mock.assert_called_once_with(["ipython", help_flag])


class TestPackageCommand:
    def test_happy_path(self, call_mock, fake_kedro_cli, mocker):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["package"])
        assert not result.exit_code, result.stdout
        call_mock.assert_has_calls(
            [
                mocker.call(
                    [sys.executable, "setup.py", "clean", "--all", "bdist_egg"],
                    cwd="src",
                ),
                mocker.call(
                    [sys.executable, "setup.py", "clean", "--all", "bdist_wheel"],
                    cwd="src",
                ),
            ]
        )


class TestBuildDocsCommand:
    def test_happy_path(self, call_mock, python_call_mock, fake_kedro_cli, mocker):
        fake_rmtree = mocker.patch("shutil.rmtree")

        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-docs"])
        assert not result.exit_code, result.stdout
        call_mock.assert_has_calls(
            [
                mocker.call(
                    [
                        "sphinx-apidoc",
                        "--module-first",
                        "-o",
                        "docs/source",
                        "src/fake_package",
                    ]
                ),
                mocker.call(
                    ["sphinx-build", "-M", "html", "docs/source", "docs/build", "-a"]
                ),
            ]
        )
        python_call_mock.assert_has_calls(
            [
                mocker.call("pip", ["install", "src/[docs]"]),
                mocker.call("pip", ["install", "-r", "src/requirements.txt"]),
                mocker.call("ipykernel", ["install", "--user", "--name=fake_package"]),
            ]
        )
        fake_rmtree.assert_called_once_with("docs/build", ignore_errors=True)

    @pytest.mark.parametrize("open_flag", ["-o", "--open"])
    def test_open_docs(self, open_flag, fake_kedro_cli, mocker):
        patched_browser = mocker.patch("webbrowser.open")
        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-docs", open_flag])
        assert not result.exit_code, result.stdout
        expected_path = (Path.cwd() / "docs" / "build" / "html" / "index.html").as_uri()
        patched_browser.assert_called_once_with(expected_path)


class TestBuildReqsCommand:
    def test_requirements_file_exists(self, python_call_mock, fake_kedro_cli, mocker):
        # File exists:
        mocker.patch.object(Path, "is_file", return_value=True)

        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-reqs"])
        assert not result.exit_code, result.stdout
        assert "Requirements built!" in result.stdout

        python_call_mock.assert_called_once_with(
            "piptools", ["compile", str(Path.cwd() / "src" / "requirements.in")]
        )

    def test_requirements_file_doesnt_exist(
        self, python_call_mock, fake_kedro_cli, mocker
    ):
        # File does not exist:
        mocker.patch.object(Path, "is_file", return_value=False)
        mocker.patch.object(Path, "read_text", return_value="fake requirements")
        fake_writer = mocker.patch.object(Path, "write_text")

        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-reqs"])
        assert not result.exit_code, result.stdout
        assert "Requirements built!" in result.stdout
        python_call_mock.assert_called_once_with(
            "piptools", ["compile", str(Path.cwd() / "src" / "requirements.in")]
        )
        fake_writer.assert_called_once_with("fake requirements")


class TestJupyterNotebookCommand:
    def test_default_kernel(self, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "notebook", "--ip=0.0.0.0"]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(False)
        call_mock.assert_called_once_with(
            [
                "jupyter-notebook",
                "--ip=0.0.0.0",
                "--KernelSpecManager.whitelist=['python3']",
            ]
        )

    def test_all_kernels(self, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "notebook", "--all-kernels"]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(True)
        call_mock.assert_called_once_with(["jupyter-notebook", "--ip=127.0.0.1"])

    @pytest.mark.parametrize("help_flag", ["-h", "--help"])
    def test_help(self, help_flag, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "notebook", help_flag]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_not_called()


class TestJupyterLabCommand:
    def test_default_kernel(self, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "lab", "--ip=0.0.0.0"]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(False)
        call_mock.assert_called_once_with(
            ["jupyter-lab", "--ip=0.0.0.0", "--KernelSpecManager.whitelist=['python3']"]
        )

    def test_all_kernels(self, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "lab", "--all-kernels"]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(True)
        call_mock.assert_called_once_with(["jupyter-lab", "--ip=127.0.0.1"])

    @pytest.mark.parametrize("help_flag", ["-h", "--help"])
    def test_help(self, help_flag, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["jupyter", "lab", help_flag])
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_not_called()


class TestConvertNotebookCommand:
    @staticmethod
    @pytest.fixture
    def fake_export_nodes(mocker, fake_kedro_cli):
        return mocker.patch.object(fake_kedro_cli, "export_nodes")

    @staticmethod
    @pytest.fixture
    def tmp_file_path():
        with NamedTemporaryFile() as f:
            yield Path(f.name)

    @staticmethod
    @pytest.fixture(autouse=True)
    def chdir_to_repo_root(fake_repo_path):
        os.chdir(str(fake_repo_path))

    # pylint: disable=too-many-arguments
    def test_convert_one_file_overwrite(
        self, mocker, fake_kedro_cli, fake_export_nodes, tmp_file_path, fake_repo_path
    ):
        """
        Trying to convert one file, the output file already exists,
        overwriting it.
        """
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("click.confirm", return_value=True)

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "convert", str(tmp_file_path)]
        )
        assert not result.exit_code, result.stdout

        output_prefix = fake_repo_path.resolve() / "src" / "fake_package" / "nodes"
        fake_export_nodes.assert_called_once_with(
            tmp_file_path.resolve(), output_prefix / "{}.py".format(tmp_file_path.stem)
        )

    def test_convert_one_file_do_not_overwrite(
        self, mocker, fake_kedro_cli, fake_export_nodes, tmp_file_path
    ):
        """
        Trying to convert one file, the output file already exists,
        user refuses to overwrite it.
        """
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("click.confirm", return_value=False)

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["jupyter", "convert", str(tmp_file_path)]
        )
        assert not result.exit_code, result.stdout

        fake_export_nodes.assert_not_called()

    def test_convert_all_files(
        self, mocker, fake_kedro_cli, fake_export_nodes, fake_repo_path
    ):
        """
        Trying to convert all files, the output files already exist.
        """
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("click.confirm", return_value=True)
        mocker.patch.object(
            fake_kedro_cli, "iglob", return_value=["/path/1", "/path/2"]
        )

        result = CliRunner().invoke(fake_kedro_cli.cli, ["jupyter", "convert", "--all"])
        assert not result.exit_code, result.stdout

        output_prefix = (fake_repo_path / "src" / "fake_package" / "nodes").resolve()
        fake_export_nodes.assert_has_calls(
            [
                mocker.call(Path("/path/1"), output_prefix / "1.py"),
                mocker.call(Path("/path/2"), output_prefix / "2.py"),
            ]
        )
