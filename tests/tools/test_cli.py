"""Testing module for CLI tools"""
import shutil
from collections import namedtuple
from pathlib import Path

import pytest

from kedro import __version__ as kedro_version
from kedro.framework.cli.cli import KedroCLI, cli
from kedro.framework.startup import ProjectMetadata
from tools.cli import get_cli_structure

REPO_NAME = "cli_tools_dummy_project"
PACKAGE_NAME = "cli_tools_dummy_package"
DEFAULT_KEDRO_COMMANDS = [
    "catalog",
    "ipython",
    "jupyter",
    "new",
    "package",
    "pipeline",
    "micropkg",
    "registry",
    "run",
    "starter",
]


@pytest.fixture
def fake_root_dir(tmp_path):
    try:
        yield Path(tmp_path).resolve()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def fake_metadata(fake_root_dir):
    metadata = ProjectMetadata(
        fake_root_dir / REPO_NAME / "pyproject.toml",
        PACKAGE_NAME,
        "CLI Tools Testing Project",
        fake_root_dir / REPO_NAME,
        kedro_version,
        fake_root_dir / REPO_NAME / "src",
        kedro_version,
    )
    return metadata


class TestCLITools:
    def test_get_cli_structure_raw(self, mocker, fake_metadata):
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
        raw_cli_structure = get_cli_structure(kedro_cli, get_help=False)

        # raw CLI structure tests
        assert isinstance(raw_cli_structure, dict)
        assert isinstance(raw_cli_structure["kedro"], dict)

        for k, v in raw_cli_structure["kedro"].items():
            assert isinstance(k, str)
            assert isinstance(v, dict)

        assert sorted(list(raw_cli_structure["kedro"])) == sorted(
            DEFAULT_KEDRO_COMMANDS
        )

    def test_get_cli_structure_depth(self, mocker, fake_metadata):
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
        raw_cli_structure = get_cli_structure(kedro_cli, get_help=False)
        assert isinstance(raw_cli_structure["kedro"]["new"], dict)
        assert sorted(list(raw_cli_structure["kedro"]["new"].keys())) == sorted(
            [
                "--verbose",
                "-v",
                "--config",
                "-c",
                "--addons",
                "-a",
                "--starter",
                "-s",
                "--checkout",
                "--directory",
                "--help",
            ]
        )
        # now check that once params and args are reached, the values are None
        assert raw_cli_structure["kedro"]["new"]["--starter"] is None
        assert raw_cli_structure["kedro"]["new"]["--checkout"] is None
        assert raw_cli_structure["kedro"]["new"]["--help"] is None
        assert raw_cli_structure["kedro"]["new"]["-c"] is None

    def test_get_cli_structure_help(self, mocker, fake_metadata):
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
        help_cli_structure = get_cli_structure(kedro_cli, get_help=True)

        assert isinstance(help_cli_structure, dict)
        assert isinstance(help_cli_structure["kedro"], dict)

        for k, v in help_cli_structure["kedro"].items():
            assert isinstance(k, str)
            if isinstance(v, dict):
                for sub_key in v:
                    assert isinstance(help_cli_structure["kedro"][k][sub_key], str)
                    assert help_cli_structure["kedro"][k][sub_key].startswith(
                        "Usage:  [OPTIONS]"
                    )
            elif isinstance(v, str):
                assert v.startswith("Usage:  [OPTIONS]")

        assert sorted(list(help_cli_structure["kedro"])) == sorted(
            DEFAULT_KEDRO_COMMANDS
        )
