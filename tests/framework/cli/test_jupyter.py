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
import json
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from click.testing import CliRunner
from jupyter_client.kernelspec import NATIVE_KERNEL_NAME, KernelSpecManager

from kedro.framework.cli.jupyter import (
    SingleKernelSpecManager,
    _export_nodes,
    collect_line_magic,
)
from kedro.framework.cli.utils import KedroCliError


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


def test_collect_line_magic(entry_points, entry_point):
    entry_point.load.return_value = "line_magic"
    line_magics = collect_line_magic()
    assert line_magics == ["line_magic"]
    entry_points.assert_called_once_with(group="kedro.line_magic")


class TestSingleKernelSpecManager:
    def test_overridden_values(self):
        assert SingleKernelSpecManager.whitelist == [NATIVE_KERNEL_NAME]

    def test_renaming_default_kernel(self, mocker):
        """
        Make sure the default kernel display_name is changed.
        """
        mocker.patch.object(
            KernelSpecManager,
            "get_kernel_spec",
            return_value=mocker.Mock(display_name="default"),
        )
        manager = SingleKernelSpecManager()
        manager.default_kernel_name = "New Kernel Name"
        new_kernel_spec = manager.get_kernel_spec(NATIVE_KERNEL_NAME)
        assert new_kernel_spec.display_name == "New Kernel Name"

    def test_non_default_kernel_untouched(self, mocker):
        """
        Make sure the non-default kernel display_name is not changed.
        In theory the function will never be called like that,
        but let's not make extra assumptions.
        """
        mocker.patch.object(
            KernelSpecManager,
            "get_kernel_spec",
            return_value=mocker.Mock(display_name="default"),
        )
        manager = SingleKernelSpecManager()
        manager.default_kernel_name = "New Kernel Name"
        new_kernel_spec = manager.get_kernel_spec("another_kernel")
        assert new_kernel_spec.display_name == "default"


def default_jupyter_options(command, address="127.0.0.1", all_kernels=False):
    cmd = [
        command,
        "--ip",
        address,
        "--MappingKernelManager.cull_idle_timeout=30",
        "--MappingKernelManager.cull_interval=30",
    ]

    if not all_kernels:
        cmd += [
            "--NotebookApp.kernel_spec_manager_class="
            "kedro.framework.cli.jupyter.SingleKernelSpecManager",
            "--KernelSpecManager.default_kernel_name='CLITestingProject'",
        ]

    return "jupyter", cmd


@pytest.fixture(autouse=True)
def python_call_mock(mocker):
    return mocker.patch("kedro.framework.cli.jupyter.python_call")


@pytest.fixture
def fake_ipython_message(mocker):
    return mocker.patch("kedro.framework.cli.jupyter.ipython_message")


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestJupyterNotebookCommand:
    def test_default_kernel(
        self, python_call_mock, fake_project_cli, fake_ipython_message, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "notebook", "--ip", "0.0.0.0"],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(False)
        python_call_mock.assert_called_once_with(
            *default_jupyter_options("notebook", "0.0.0.0")
        )

    def test_all_kernels(
        self, python_call_mock, fake_project_cli, fake_ipython_message, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "notebook", "--all-kernels"],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(True)
        python_call_mock.assert_called_once_with(
            *default_jupyter_options("notebook", all_kernels=True)
        )

    @pytest.mark.parametrize("help_flag", ["-h", "--help"])
    def test_help(
        self, help_flag, fake_project_cli, fake_ipython_message, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["jupyter", "notebook", help_flag], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_not_called()

    @pytest.mark.parametrize("env_flag", ["--env", "-e"])
    def test_env(self, env_flag, fake_project_cli, python_call_mock, fake_metadata):
        """This tests passing an environment variable to the jupyter subprocess."""
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "notebook", env_flag, "base"],
            obj=fake_metadata,
        )
        assert not result.exit_code

        args, kwargs = python_call_mock.call_args
        assert args == default_jupyter_options("notebook")
        assert "env" in kwargs
        assert kwargs["env"]["KEDRO_ENV"] == "base"

    def test_fail_no_jupyter_core(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"jupyter_core": None})
        result = CliRunner().invoke(fake_project_cli, ["jupyter", "notebook"])

        assert result.exit_code
        error = (
            "Module `jupyter_core` not found. Make sure to install required project "
            "dependencies by running the `kedro install` command first."
        )
        assert error in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestJupyterLabCommand:
    def test_default_kernel(
        self, python_call_mock, fake_project_cli, fake_ipython_message, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "lab", "--ip", "0.0.0.0"],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(False)
        python_call_mock.assert_called_once_with(
            *default_jupyter_options("lab", "0.0.0.0")
        )

    def test_all_kernels(
        self, python_call_mock, fake_project_cli, fake_ipython_message, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["jupyter", "lab", "--all-kernels"], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_called_once_with(True)
        python_call_mock.assert_called_once_with(
            *default_jupyter_options("lab", all_kernels=True)
        )

    @pytest.mark.parametrize("help_flag", ["-h", "--help"])
    def test_help(
        self, help_flag, fake_project_cli, fake_ipython_message, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["jupyter", "lab", help_flag], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        fake_ipython_message.assert_not_called()

    @pytest.mark.parametrize("env_flag", ["--env", "-e"])
    def test_env(self, env_flag, fake_project_cli, python_call_mock, fake_metadata):
        """This tests passing an environment variable to the jupyter subprocess."""
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "lab", env_flag, "base"],
            obj=fake_metadata,
        )
        assert not result.exit_code

        args, kwargs = python_call_mock.call_args
        assert args == default_jupyter_options("lab")
        assert "env" in kwargs
        assert kwargs["env"]["KEDRO_ENV"] == "base"

    def test_fail_no_jupyter_core(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"jupyter_core": None})
        result = CliRunner().invoke(fake_project_cli, ["jupyter", "lab"])

        assert result.exit_code
        error = (
            "Module `jupyter_core` not found. Make sure to install required project "
            "dependencies by running the `kedro install` command first."
        )
        assert error in result.output


@pytest.fixture
def cleanup_nodes_dir(fake_package_path):
    yield
    nodes_dir = fake_package_path / "nodes"
    if nodes_dir.exists():
        shutil.rmtree(str(nodes_dir))


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "cleanup_nodes_dir")
class TestConvertNotebookCommand:
    @pytest.fixture
    def fake_export_nodes(self, mocker):
        return mocker.patch("kedro.framework.cli.jupyter._export_nodes")

    @pytest.fixture
    def tmp_file_path(self):
        with NamedTemporaryFile() as f:
            yield Path(f.name)

    # pylint: disable=too-many-arguments
    def test_convert_one_file_overwrite(
        self,
        mocker,
        fake_project_cli,
        fake_export_nodes,
        tmp_file_path,
        fake_package_path,
        fake_metadata,
    ):
        """
        Trying to convert one file, the output file already exists,
        overwriting it.
        """
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("click.confirm", return_value=True)
        output_dir = fake_package_path / "nodes"
        assert not output_dir.exists()

        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "convert", str(tmp_file_path)],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout

        assert (output_dir / "__init__.py").is_file()
        fake_export_nodes.assert_called_once_with(
            tmp_file_path.resolve(), output_dir / f"{tmp_file_path.stem}.py"
        )

    def test_convert_one_file_do_not_overwrite(
        self, mocker, fake_project_cli, fake_export_nodes, tmp_file_path, fake_metadata
    ):
        """
        Trying to convert one file, the output file already exists,
        user refuses to overwrite it.
        """
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("click.confirm", return_value=False)

        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "convert", str(tmp_file_path)],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout

        fake_export_nodes.assert_not_called()

    def test_convert_all_files(
        self,
        mocker,
        fake_project_cli,
        fake_export_nodes,
        fake_package_path,
        fake_metadata,
    ):
        """Trying to convert all files, the output files already exist."""
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("click.confirm", return_value=True)
        mocker.patch(
            "kedro.framework.cli.jupyter.iglob", return_value=["/path/1", "/path/2"]
        )
        output_dir = fake_package_path / "nodes"
        assert not output_dir.exists()

        result = CliRunner().invoke(
            fake_project_cli, ["jupyter", "convert", "--all"], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout

        assert (output_dir / "__init__.py").is_file()
        fake_export_nodes.assert_has_calls(
            [
                mocker.call(Path("/path/1"), output_dir / "1.py"),
                mocker.call(Path("/path/2"), output_dir / "2.py"),
            ]
        )

    def test_convert_without_filepath_and_all_flag(
        self, fake_project_cli, fake_metadata
    ):
        """Neither path nor --all flag is provided."""
        result = CliRunner().invoke(
            fake_project_cli, ["jupyter", "convert"], obj=fake_metadata
        )
        expected_output = (
            "Please specify a notebook filepath or "
            "add '--all' to convert all notebooks.\n"
        )
        assert result.exit_code
        assert result.stdout == expected_output

    def test_non_unique_notebook_names_error(
        self, fake_project_cli, mocker, fake_metadata
    ):
        """Trying to convert notebooks with the same name."""
        mocker.patch(
            "kedro.framework.cli.jupyter.iglob", return_value=["/path1/1", "/path2/1"]
        )

        result = CliRunner().invoke(
            fake_project_cli, ["jupyter", "convert", "--all"], obj=fake_metadata
        )

        expected_output = (
            "Error: Found non-unique notebook names! Please rename the following: 1\n"
        )
        assert result.exit_code
        assert expected_output in result.output

    def test_convert_one_file(
        self,
        fake_project_cli,
        fake_export_nodes,
        tmp_file_path,
        fake_package_path,
        fake_metadata,
    ):
        """Trying to convert one file, the output file doesn't exist."""
        output_dir = fake_package_path / "nodes"
        assert not output_dir.exists()

        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "convert", str(tmp_file_path)],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout

        assert (output_dir / "__init__.py").is_file()
        fake_export_nodes.assert_called_once_with(
            tmp_file_path.resolve(), output_dir / f"{tmp_file_path.stem}.py"
        )

    def test_convert_one_file_nodes_directory_exists(
        self,
        fake_project_cli,
        fake_export_nodes,
        tmp_file_path,
        fake_package_path,
        fake_metadata,
    ):
        """User-created nodes/ directory is used as is."""
        output_dir = fake_package_path / "nodes"
        assert not output_dir.exists()
        output_dir.mkdir()

        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "convert", str(tmp_file_path)],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout

        assert not (output_dir / "__init__.py").is_file()
        fake_export_nodes.assert_called_once_with(
            tmp_file_path.resolve(), output_dir / f"{tmp_file_path.stem}.py"
        )


class TestExportNodes:
    @pytest.fixture
    def project_path(self, tmp_path):
        temp = Path(str(tmp_path))
        return Path(temp / "some/path/to/my_project")

    @pytest.fixture
    def nodes_path(self, project_path):
        path = project_path / "src/my_project/nodes"
        path.mkdir(parents=True)
        return path

    def test_export_nodes(self, project_path, nodes_path):
        nodes = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": "print('hello world')",
                        "metadata": {"tags": ["node"]},
                    },
                    {
                        "cell_type": "code",
                        "source": "print(10+5)",
                        "metadata": {"tags": ["node"]},
                    },
                    {"cell_type": "code", "source": "a = 10", "metadata": {}},
                ]
            }
        )
        notebook_file = project_path / "notebook.ipynb"
        notebook_file.write_text(nodes)

        output_path = nodes_path / f"{notebook_file.stem}.py"
        _export_nodes(notebook_file, output_path)

        assert output_path.is_file()
        assert output_path.read_text() == "print('hello world')\nprint(10+5)\n"

    def test_export_nodes_different_notebook_paths(self, project_path, nodes_path):
        nodes = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": "print('hello world')",
                        "metadata": {"tags": ["node"]},
                    }
                ]
            }
        )
        notebook_file1 = project_path / "notebook1.ipynb"
        notebook_file1.write_text(nodes)
        output_path1 = nodes_path / "notebook1.py"

        notebook_file2 = nodes_path / "notebook2.ipynb"
        notebook_file2.write_text(nodes)
        output_path2 = nodes_path / "notebook2.py"

        _export_nodes(notebook_file1, output_path1)
        _export_nodes(notebook_file2, output_path2)

        assert output_path1.read_text() == "print('hello world')\n"
        assert output_path2.read_text() == "print('hello world')\n"

    def test_export_nodes_nothing_to_write(self, project_path, nodes_path):
        nodes = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": "print('hello world')",
                        "metadata": {},
                    },
                    {
                        "cell_type": "text",
                        "source": "hello world",
                        "metadata": {"tags": ["node"]},
                    },
                ]
            }
        )
        notebook_file = project_path / "notebook.iypnb"
        notebook_file.write_text(nodes)

        with pytest.warns(UserWarning, match="Skipping notebook"):
            output_path = nodes_path / f"{notebook_file.stem}.py"
            _export_nodes(notebook_file, output_path)

        output_path = nodes_path / "notebook.py"
        assert not output_path.exists()

    def test_export_nodes_overwrite(self, project_path, nodes_path):
        existing_nodes = nodes_path / "notebook.py"
        existing_nodes.touch()
        existing_nodes.write_text("original")

        nodes = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": "print('hello world')",
                        "metadata": {"tags": ["node"]},
                    }
                ]
            }
        )
        notebook_file = project_path / "notebook.iypnb"
        notebook_file.write_text(nodes)

        output_path = nodes_path / f"{notebook_file.stem}.py"
        _export_nodes(notebook_file, output_path)

        assert output_path.is_file()
        assert output_path.read_text() == "print('hello world')\n"

    def test_export_nodes_json_error(self, nodes_path):
        random_file = nodes_path / "notebook.txt"
        random_file.touch()
        random_file.write_text("original")
        output_path = nodes_path / f"{random_file.stem}.py"

        pattern = "Provided filepath is not a Jupyter notebook"
        with pytest.raises(KedroCliError, match=pattern):
            _export_nodes(random_file, output_path)
