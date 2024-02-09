import json
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from click.testing import CliRunner
from jupyter_client.kernelspec import (
    KernelSpecManager,
    find_kernel_specs,
    get_kernel_spec,
)

from kedro.framework.cli.jupyter import _create_kernel, _export_nodes
from kedro.framework.cli.utils import KedroCliError


@pytest.fixture(autouse=True)
def python_call_mock(mocker):
    return mocker.patch("kedro.framework.cli.jupyter.python_call")


@pytest.fixture
def create_kernel_mock(mocker):
    return mocker.patch("kedro.framework.cli.jupyter._create_kernel")


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "create_kernel_mock", "python_call_mock"
)
class TestJupyterSetupCommand:
    def test_happy_path(self, fake_project_cli, fake_metadata, create_kernel_mock):
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "setup"],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        kernel_name = f"kedro_{fake_metadata.package_name}"
        display_name = f"Kedro ({fake_metadata.package_name})"
        create_kernel_mock.assert_called_once_with(kernel_name, display_name)

    def test_fail_no_jupyter(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"notebook": None})
        result = CliRunner().invoke(fake_project_cli, ["jupyter", "notebook"])

        assert result.exit_code
        error = (
            "Module 'notebook' not found. Make sure to install required project "
            "dependencies by running the 'pip install -r src/requirements.txt' command first."
        )
        assert error in result.output


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "create_kernel_mock", "python_call_mock"
)
class TestJupyterNotebookCommand:
    def test_happy_path(
        self, python_call_mock, fake_project_cli, fake_metadata, create_kernel_mock
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "notebook", "--random-arg", "value"],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        kernel_name = f"kedro_{fake_metadata.package_name}"
        display_name = f"Kedro ({fake_metadata.package_name})"
        create_kernel_mock.assert_called_once_with(kernel_name, display_name)
        python_call_mock.assert_called_once_with(
            "jupyter",
            [
                "notebook",
                f"--MultiKernelManager.default_kernel_name={kernel_name}",
                "--random-arg",
                "value",
            ],
        )

    @pytest.mark.parametrize("env_flag,env", [("--env", "base"), ("-e", "local")])
    def test_env(self, env_flag, env, fake_project_cli, fake_metadata, mocker):
        """This tests passing an environment variable to the jupyter subprocess."""
        mock_environ = mocker.patch("os.environ", {})
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "notebook", env_flag, env],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        assert mock_environ["KEDRO_ENV"] == env

    def test_fail_no_jupyter(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"notebook": None})
        result = CliRunner().invoke(fake_project_cli, ["jupyter", "notebook"])

        assert result.exit_code
        error = (
            "Module 'notebook' not found. Make sure to install required project "
            "dependencies by running the 'pip install -r src/requirements.txt' command first."
        )
        assert error in result.output


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "create_kernel_mock", "python_call_mock"
)
class TestJupyterLabCommand:
    def test_happy_path(
        self, python_call_mock, fake_project_cli, fake_metadata, create_kernel_mock
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "lab", "--random-arg", "value"],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        kernel_name = f"kedro_{fake_metadata.package_name}"
        display_name = f"Kedro ({fake_metadata.package_name})"
        create_kernel_mock.assert_called_once_with(kernel_name, display_name)
        python_call_mock.assert_called_once_with(
            "jupyter",
            [
                "lab",
                f"--MultiKernelManager.default_kernel_name={kernel_name}",
                "--random-arg",
                "value",
            ],
        )

    @pytest.mark.parametrize("env_flag,env", [("--env", "base"), ("-e", "local")])
    def test_env(self, env_flag, env, fake_project_cli, fake_metadata, mocker):
        """This tests passing an environment variable to the jupyter subprocess."""
        mock_environ = mocker.patch("os.environ", {})
        result = CliRunner().invoke(
            fake_project_cli,
            ["jupyter", "lab", env_flag, env],
            obj=fake_metadata,
        )
        assert not result.exit_code, result.stdout
        assert mock_environ["KEDRO_ENV"] == env

    def test_fail_no_jupyter(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"jupyterlab": None})
        result = CliRunner().invoke(fake_project_cli, ["jupyter", "lab"])

        assert result.exit_code
        error = (
            "Module 'jupyterlab' not found. Make sure to install required project "
            "dependencies by running the 'pip install -r src/requirements.txt' command first."
        )
        assert error in result.output


@pytest.fixture
def cleanup_kernel():
    yield
    if "my_kernel_name" in find_kernel_specs():
        KernelSpecManager().remove_kernel_spec("my_kernel_name")


@pytest.mark.usefixtures("cleanup_kernel")
class TestCreateKernel:
    def test_create_new_kernel(self):
        _create_kernel("my_kernel_name", "My display name")
        kernel_spec = get_kernel_spec("my_kernel_name")
        assert kernel_spec.display_name == "My display name"
        assert kernel_spec.language == "python"
        assert kernel_spec.argv[-2:] == ["--ext", "kedro.ipython"]
        kernel_files = {file.name for file in Path(kernel_spec.resource_dir).iterdir()}
        assert kernel_files == {
            "kernel.json",
            "logo-32x32.png",
            "logo-64x64.png",
            "logo-svg.svg",
        }

    def test_kernel_install_replaces(self):
        _create_kernel("my_kernel_name", "My display name 1")
        _create_kernel("my_kernel_name", "My display name 2")
        kernel_spec = get_kernel_spec("my_kernel_name")
        assert kernel_spec.display_name == "My display name 2"

    def test_error(self, mocker):
        mocker.patch("ipykernel.kernelspec.install", side_effect=ValueError)
        pattern = "Cannot setup kedro kernel for Jupyter"
        with pytest.raises(KedroCliError, match=pattern):
            _create_kernel("my_kernel_name", "My display name")


@pytest.fixture
def cleanup_nodes_dir(fake_package_path):
    yield
    nodes_dir = fake_package_path / "nodes"
    if nodes_dir.exists():
        shutil.rmtree(str(nodes_dir))


@pytest.mark.usefixtures("chdir_to_dummy_project", "cleanup_nodes_dir")
class TestConvertNotebookCommand:
    @pytest.fixture
    def fake_export_nodes(self, mocker):
        return mocker.patch("kedro.framework.cli.jupyter._export_nodes")

    @pytest.fixture
    def tmp_file_path(self):
        with NamedTemporaryFile() as f:
            yield Path(f.name)

    # noqa: PLR0913
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
        assert expected_output in result.stdout

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
