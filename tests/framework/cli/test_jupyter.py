import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from jupyter_client.kernelspec import (
    KernelSpecManager,
    find_kernel_specs,
    get_kernel_spec,
)

from kedro.framework.cli.jupyter import _create_kernel
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
            "dependencies by running the 'pip install -r requirements.txt' command first."
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
            "dependencies by running the 'pip install -r requirements.txt' command first."
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
            "dependencies by running the 'pip install -r requirements.txt' command first."
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
