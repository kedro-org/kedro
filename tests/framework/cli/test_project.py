# pylint: disable=unused-argument
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def call_mock(mocker):
    return mocker.patch("kedro.framework.cli.project.call")


@pytest.fixture
def fake_copyfile(mocker):
    return mocker.patch("shutil.copyfile")


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestIpythonCommand:
    def test_happy_path(
        self,
        call_mock,
        fake_project_cli,
        fake_repo_path,
        fake_metadata,
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["ipython", "--random-arg", "value"], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        call_mock.assert_called_once_with(
            [
                "ipython",
                "--ext",
                "kedro.ipython",
                "--random-arg",
                "value",
            ]
        )

    @pytest.mark.parametrize("env_flag,env", [("--env", "base"), ("-e", "local")])
    def test_env(
        self,
        env_flag,
        env,
        fake_project_cli,
        mocker,
        fake_metadata,
    ):
        """This tests starting ipython with specific env."""
        mock_environ = mocker.patch("os.environ", {})
        result = CliRunner().invoke(
            fake_project_cli, ["ipython", env_flag, env], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        assert mock_environ["KEDRO_ENV"] == env

    def test_fail_no_ipython(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"IPython": None})
        result = CliRunner().invoke(fake_project_cli, ["ipython"])

        assert result.exit_code
        error = (
            "Module 'IPython' not found. Make sure to install required project "
            "dependencies by running the 'pip install -r src/requirements.txt' command first."
        )
        assert error in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestPackageCommand:
    def test_happy_path(
        self, call_mock, fake_project_cli, mocker, fake_repo_path, fake_metadata
    ):
        result = CliRunner().invoke(fake_project_cli, ["package"], obj=fake_metadata)
        assert not result.exit_code, result.stdout
        call_mock.assert_has_calls(
            [
                mocker.call(
                    [
                        sys.executable,
                        "-m",
                        "build",
                        "--wheel",
                        "--outdir",
                        "../dist",
                    ],
                    cwd=str(fake_repo_path / "src"),
                ),
                mocker.call(
                    [
                        "tar",
                        "--exclude=local/*.yml",
                        "-czf",
                        f"dist/conf-{fake_metadata.package_name}.tar.gz",
                        f"--directory={fake_metadata.project_path}",
                        "conf",
                    ],
                ),
            ]
        )

    def test_happy_path(
        self,
        call_mock,
        python_call_mock,
        fake_project_cli,
        mocker,
        fake_repo_path,
        fake_metadata,
    ):
        fake_rmtree = mocker.patch("shutil.rmtree")

        result = CliRunner().invoke(fake_project_cli, ["build-docs"], obj=fake_metadata)
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
    def test_open_docs(self, open_flag, fake_project_cli, mocker, fake_metadata):
        mocker.patch("shutil.rmtree")
        patched_browser = mocker.patch("webbrowser.open")
        result = CliRunner().invoke(
            fake_project_cli, ["build-docs", open_flag], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        expected_path = (Path.cwd() / "docs" / "build" / "html" / "index.html").as_uri()
        patched_browser.assert_called_once_with(expected_path)
