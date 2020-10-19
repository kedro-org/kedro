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
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from kedro.framework.cli.project import NO_DEPENDENCY_MESSAGE


@pytest.fixture(autouse=True)
def call_mock(mocker):
    return mocker.patch("kedro.framework.cli.project.call")


@pytest.fixture(autouse=True)
def python_call_mock(mocker):
    return mocker.patch("kedro.framework.cli.project.python_call")


@pytest.fixture
def fake_ipython_message(mocker):
    return mocker.patch("kedro.framework.cli.project.ipython_message")


@pytest.fixture
def fake_copyfile(mocker):
    return mocker.patch("shutil.copyfile")


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
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

    def test_nbstripout_not_installed(self, fake_kedro_cli, fake_git_repo, mocker):
        """
        Run activate-nbstripout target without nbstripout installed
        There should be a clear message about it.
        """
        mocker.patch.dict("sys.modules", {"nbstripout": None})

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

    def test_no_git_executable(self, fake_kedro_cli, fake_nbstripout, mocker):
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)
        result = CliRunner().invoke(fake_kedro_cli.cli, ["activate-nbstripout"])

        assert result.exit_code
        assert "Git executable not found. Install Git first." in result.stdout


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestTestCommand:
    def test_happy_path(self, fake_kedro_cli, python_call_mock):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["test", "--random-arg", "value"]
        )
        assert not result.exit_code
        python_call_mock.assert_called_once_with("pytest", ("--random-arg", "value"))

    def test_pytest_not_installed(
        self, fake_kedro_cli, python_call_mock, mocker, fake_repo_path
    ):
        mocker.patch.dict("sys.modules", {"pytest": None})

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["test", "--random-arg", "value"]
        )
        expected_message = NO_DEPENDENCY_MESSAGE.format(
            module="pytest", src=str(fake_repo_path / "src")
        )

        assert result.exit_code
        assert expected_message in result.stdout
        python_call_mock.assert_not_called()


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestLintCommand:
    @pytest.mark.parametrize("files", [(), ("src",)])
    def test_lint(
        self, fake_kedro_cli, python_call_mock, files, mocker, fake_repo_path
    ):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["lint", *files])
        assert not result.exit_code, result.stdout

        expected_files = files or (
            str(fake_repo_path / "src/tests"),
            str(fake_repo_path / "src/dummy_package"),
        )
        expected_calls = [
            mocker.call("black", expected_files),
            mocker.call("flake8", expected_files),
            mocker.call("isort", ("-rc",) + expected_files),
        ]

        assert python_call_mock.call_args_list == expected_calls

    @pytest.mark.parametrize(
        "check_flag,files",
        [
            ("-c", ()),
            ("--check-only", ()),
            ("-c", ("src",)),
            ("--check-only", ("src",)),
        ],
    )
    def test_lint_check_only(
        self,
        fake_kedro_cli,
        python_call_mock,
        check_flag,
        mocker,
        files,
        fake_repo_path,
    ):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["lint", check_flag, *files])
        assert not result.exit_code, result.stdout

        expected_files = files or (
            str(fake_repo_path / "src/tests"),
            str(fake_repo_path / "src/dummy_package"),
        )
        expected_calls = [
            mocker.call("black", ("--check",) + expected_files),
            mocker.call("flake8", expected_files),
            mocker.call("isort", ("-c", "-rc") + expected_files),
        ]

        assert python_call_mock.call_args_list == expected_calls

    @pytest.mark.parametrize("module_name", ["flake8", "isort"])
    def test_import_not_installed(
        self, fake_kedro_cli, python_call_mock, module_name, mocker, fake_repo_path
    ):
        mocker.patch.dict("sys.modules", {module_name: None})

        result = CliRunner().invoke(fake_kedro_cli.cli, ["lint"])
        expected_message = NO_DEPENDENCY_MESSAGE.format(
            module=module_name, src=str(fake_repo_path / "src")
        )

        assert result.exit_code, result.stdout
        assert expected_message in result.stdout
        python_call_mock.assert_not_called()

    def test_pythonpath_env_var(self, fake_kedro_cli, mocker, fake_repo_path):
        mocked_environ = mocker.patch("os.environ", {})
        CliRunner().invoke(fake_kedro_cli.cli, ["lint"])
        assert mocked_environ == {"PYTHONPATH": str(fake_repo_path / "src")}


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "fake_copyfile")
class TestInstallCommand:
    def test_install_compile_default(
        self, python_call_mock, fake_kedro_cli, fake_repo_path, fake_copyfile, mocker,
    ):
        """Test that the requirements are compiled by default
        if requirements.in doesn't exist"""
        mocker.patch("kedro.framework.cli.project.os").name = "posix"
        result = CliRunner().invoke(fake_kedro_cli.cli, ["install"])
        assert not result.exit_code, result.output
        assert "Requirements installed!" in result.output

        requirements_in = fake_repo_path / "src" / "requirements.in"
        requirements_txt = fake_repo_path / "src" / "requirements.txt"
        expected_calls = [
            mocker.call("piptools", ["compile", "-q", str(requirements_in)]),
            mocker.call("pip", ["install", "-U", "-r", str(requirements_txt)]),
        ]
        assert python_call_mock.mock_calls == expected_calls
        fake_copyfile.assert_called_once_with(
            str(requirements_txt), str(requirements_in)
        )

    def test_install_compile_force(
        self, python_call_mock, fake_kedro_cli, fake_repo_path, fake_copyfile, mocker,
    ):
        """Test that the requirements are compiled if requirements.in exists
        and --build-reqs CLI option is specified"""
        mocker.patch("kedro.framework.cli.project.os").name = "posix"
        mocker.patch.object(Path, "is_file", return_value=True)
        result = CliRunner().invoke(fake_kedro_cli.cli, ["install", "--build-reqs"])
        assert not result.exit_code, result.output
        assert "Requirements installed!" in result.output

        requirements_in = fake_repo_path / "src" / "requirements.in"
        requirements_txt = fake_repo_path / "src" / "requirements.txt"
        expected_calls = [
            mocker.call("piptools", ["compile", "-q", str(requirements_in)]),
            mocker.call("pip", ["install", "-U", "-r", str(requirements_txt)]),
        ]
        assert python_call_mock.mock_calls == expected_calls
        fake_copyfile.assert_not_called()

    def test_install_no_compile_default(
        self, python_call_mock, fake_kedro_cli, fake_repo_path, fake_copyfile, mocker,
    ):
        """Test that the requirements aren't compiled by default
        if requirements.in exists"""
        mocker.patch("kedro.framework.cli.project.os").name = "posix"
        mocker.patch.object(Path, "is_file", return_value=True)
        result = CliRunner().invoke(fake_kedro_cli.cli, ["install"])
        assert not result.exit_code, result.output
        assert "Requirements installed!" in result.output

        requirements_txt = fake_repo_path / "src" / "requirements.txt"
        python_call_mock.assert_called_once_with(
            "pip", ["install", "-U", "-r", str(requirements_txt)]
        )
        fake_copyfile.assert_not_called()

    def test_install_no_compile_force(
        self, python_call_mock, fake_kedro_cli, fake_repo_path, fake_copyfile, mocker
    ):
        """Test that the requirements aren't compiled if requirements.in doesn't exist
        and --no-build-reqs CLI option is specified"""
        mocker.patch("kedro.framework.cli.project.os").name = "posix"
        result = CliRunner().invoke(fake_kedro_cli.cli, ["install", "--no-build-reqs"])
        assert not result.exit_code, result.output
        assert "Requirements installed!" in result.output

        requirements_txt = fake_repo_path / "src" / "requirements.txt"
        python_call_mock.assert_called_once_with(
            "pip", ["install", "-U", "-r", str(requirements_txt)]
        )
        fake_copyfile.assert_not_called()

    def test_with_env_file(
        self,
        python_call_mock,
        call_mock,
        fake_kedro_cli,
        mocker,
        fake_repo_path,
        fake_copyfile,
    ):
        mocker.patch("kedro.framework.cli.project.os").name = "posix"
        # Pretend env file exists:
        mocker.patch.object(Path, "is_file", return_value=True)

        result = CliRunner().invoke(fake_kedro_cli.cli, ["install"])
        assert not result.exit_code, result.stdout
        assert "Requirements installed!" in result.output

        requirements_txt = fake_repo_path / "src" / "requirements.txt"
        expected_calls = [
            mocker.call("pip", ["install", "-U", "-r", str(requirements_txt)])
        ]
        assert python_call_mock.mock_calls == expected_calls

        call_mock.assert_called_once_with(
            [
                "conda",
                "env",
                "update",
                "--file",
                str(fake_repo_path / "src/environment.yml"),
                "--prune",
            ]
        )
        fake_copyfile.assert_not_called()

    def test_windows(self, fake_kedro_cli, mocker, fake_repo_path, fake_copyfile):
        mock_subprocess = mocker.patch("kedro.framework.cli.project.subprocess")
        # pretend we are on Windows
        mocker.patch("kedro.framework.cli.project.os").name = "nt"

        result = CliRunner().invoke(fake_kedro_cli.cli, ["install"])
        assert not result.exit_code, result.stdout
        assert "Requirements installed!" in result.output

        requirements_in = fake_repo_path / "src" / "requirements.in"
        requirements_txt = fake_repo_path / "src" / "requirements.txt"
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "-r",
            str(requirements_txt),
        ]
        mock_subprocess.Popen.assert_called_once_with(
            command, creationflags=mock_subprocess.CREATE_NEW_CONSOLE
        )
        fake_copyfile.assert_called_once_with(
            str(requirements_txt), str(requirements_in)
        )


@pytest.fixture
def os_mock(mocker):
    return mocker.patch("kedro.framework.cli.project.os")


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "os_mock")
class TestIpythonCommand:
    def test_happy_path(
        self, call_mock, fake_kedro_cli, fake_ipython_message, os_mock, fake_repo_path
    ):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["ipython", "--random-arg", "value"]
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with()
        call_mock.assert_called_once_with(["ipython", "--random-arg", "value"])
        os_mock.environ.__setitem__.assert_called_once_with(
            "IPYTHONDIR", str(fake_repo_path / ".ipython")
        )

    @pytest.mark.parametrize("help_flag", ["-h", "--help"])
    def test_help(self, help_flag, call_mock, fake_kedro_cli, fake_ipython_message):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["ipython", help_flag])
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_not_called()
        call_mock.assert_called_once_with(["ipython", help_flag])

    @pytest.mark.parametrize("env_flag,env", [("--env", "base"), ("-e", "local")])
    def test_env(
        self, env_flag, env, fake_kedro_cli, call_mock, fake_repo_path, os_mock, mocker
    ):
        """This tests starting ipython with specific env."""
        result = CliRunner().invoke(fake_kedro_cli.cli, ["ipython", env_flag, env])
        assert not result.exit_code, result.stdout

        calls = [
            mocker.call("IPYTHONDIR", str(fake_repo_path / ".ipython")),
            mocker.call("KEDRO_ENV", env),
        ]
        os_mock.environ.__setitem__.assert_has_calls(calls)

    def test_load_context_error(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["ipython", "--env", "fake_env"]
        )

        expected_output = (
            "Error: Unable to load Kedro context with environment `fake_env`. "
            "Make sure it exists in the project configuration.\n"
        )
        assert result.exit_code
        assert expected_output in result.output

    def test_fail_no_ipython(self, fake_kedro_cli, mocker):
        mocker.patch.dict("sys.modules", {"IPython": None})
        result = CliRunner().invoke(fake_kedro_cli.cli, ["ipython"])

        assert result.exit_code
        error = (
            "Module `IPython` not found. Make sure to install required project "
            "dependencies by running the `kedro install` command first."
        )
        assert error in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPackageCommand:
    def test_happy_path(self, call_mock, fake_kedro_cli, mocker, fake_repo_path):
        result = CliRunner().invoke(fake_kedro_cli.cli, ["package"])
        assert not result.exit_code, result.stdout
        call_mock.assert_has_calls(
            [
                mocker.call(
                    [sys.executable, "setup.py", "clean", "--all", "bdist_egg"],
                    cwd=str(fake_repo_path / "src"),
                ),
                mocker.call(
                    [sys.executable, "setup.py", "clean", "--all", "bdist_wheel"],
                    cwd=str(fake_repo_path / "src"),
                ),
            ]
        )


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestBuildDocsCommand:
    def test_happy_path(
        self, call_mock, python_call_mock, fake_kedro_cli, mocker, fake_repo_path
    ):
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
                        str(fake_repo_path / "src/dummy_package"),
                    ]
                ),
                mocker.call(
                    ["sphinx-build", "-M", "html", "docs/source", "docs/build", "-a"]
                ),
            ]
        )
        python_call_mock.assert_has_calls(
            [
                mocker.call("pip", ["install", str(fake_repo_path / "src/[docs]")]),
                mocker.call(
                    "pip",
                    ["install", "-r", str(fake_repo_path / "src/requirements.txt")],
                ),
                mocker.call("ipykernel", ["install", "--user", "--name=dummy_package"]),
            ]
        )
        fake_rmtree.assert_called_once_with("docs/build", ignore_errors=True)

    @pytest.mark.parametrize("open_flag", ["-o", "--open"])
    def test_open_docs(self, open_flag, fake_kedro_cli, mocker):
        mocker.patch("shutil.rmtree")
        patched_browser = mocker.patch("webbrowser.open")
        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-docs", open_flag])
        assert not result.exit_code, result.stdout
        expected_path = (Path.cwd() / "docs" / "build" / "html" / "index.html").as_uri()
        patched_browser.assert_called_once_with(expected_path)


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "fake_copyfile")
class TestBuildReqsCommand:
    def test_requirements_file_exists(
        self, python_call_mock, fake_kedro_cli, mocker, fake_repo_path, fake_copyfile
    ):
        # File exists:
        mocker.patch.object(Path, "is_file", return_value=True)

        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-reqs"])
        assert not result.exit_code, result.stdout
        assert "Requirements built!" in result.stdout

        python_call_mock.assert_called_once_with(
            "piptools",
            ["compile", "-q", str(fake_repo_path / "src" / "requirements.in")],
        )
        fake_copyfile.assert_not_called()

    def test_requirements_file_doesnt_exist(
        self, python_call_mock, fake_kedro_cli, fake_repo_path, fake_copyfile
    ):
        # File does not exist:
        requirements_in = fake_repo_path / "src" / "requirements.in"
        requirements_txt = fake_repo_path / "src" / "requirements.txt"

        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-reqs"])
        assert not result.exit_code, result.stdout
        assert "Requirements built!" in result.stdout
        python_call_mock.assert_called_once_with(
            "piptools", ["compile", "-q", str(requirements_in)]
        )
        fake_copyfile.assert_called_once_with(
            str(requirements_txt), str(requirements_in)
        )

    @pytest.mark.parametrize(
        "extra_args", [["--generate-hashes"], ["-foo", "--bar", "baz"]]
    )
    def test_extra_args(
        self, python_call_mock, fake_kedro_cli, fake_repo_path, extra_args
    ):
        requirements_in = fake_repo_path / "src" / "requirements.in"

        result = CliRunner().invoke(fake_kedro_cli.cli, ["build-reqs"] + extra_args)
        assert not result.exit_code, result.stdout
        assert "Requirements built!" in result.stdout

        call_args = ["compile", "-q"] + extra_args + [str(requirements_in)]
        python_call_mock.assert_called_once_with("piptools", call_args)
