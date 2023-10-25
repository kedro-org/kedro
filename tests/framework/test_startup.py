import os
import re
import sys
from pathlib import Path

import pytest
import toml

from kedro import __version__ as kedro_version
from kedro.framework.startup import (
    ProjectMetadata,
    _get_project_metadata,
    _is_project,
    _validate_source_path,
    bootstrap_project,
)


class TestIsProject:
    project_path = Path.cwd()

    def test_no_metadata_file(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=False)

        assert not _is_project(self.project_path)

    def test_toml_invalid_format(self, tmp_path):
        """Test for loading context from an invalid path."""
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text("!!")  # Invalid TOML

        assert not _is_project(tmp_path)

    def test_non_kedro_project(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch.object(Path, "read_text", return_value="[tool]")

        assert not _is_project(self.project_path)

    def test_valid_toml_file(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = "[tool.kedro]"  # \nproject_name = 'proj'"
        mocker.patch.object(Path, "read_text", return_value=pyproject_toml_payload)

        assert _is_project(self.project_path)

    def test_toml_bad_encoding(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch.object(Path, "read_text", side_effect=UnicodeDecodeError)

        assert not _is_project(self.project_path)


class TestGetProjectMetadata:
    project_path = Path.cwd()

    def test_no_config_files(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=False)

        pattern = (
            f"Could not find the project configuration file 'pyproject.toml' "
            f"in {self.project_path}"
        )
        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            _get_project_metadata(self.project_path)

    def test_toml_invalid_format(self, tmp_path):
        """Test for loading context from an invalid path."""
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text("!!")  # Invalid TOML
        pattern = "Failed to parse 'pyproject.toml' file"
        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            _get_project_metadata(str(tmp_path))

    def test_valid_toml_file(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": kedro_version,
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)

        actual = _get_project_metadata(self.project_path)

        expected = ProjectMetadata(
            source_dir=self.project_path / "src",  # default
            config_file=self.project_path / "pyproject.toml",
            package_name="fake_package_name",
            project_name="fake_project_name",
            kedro_init_version=kedro_version,
            project_path=self.project_path,
            add_ons=None,
        )
        assert actual == expected

    # Temporary test for coverage to be removed in 0.19.0 when project_version is removed
    def test_valid_toml_file_with_project_version(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": kedro_version,
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)

        actual = _get_project_metadata(self.project_path)

        expected = ProjectMetadata(
            source_dir=self.project_path / "src",  # default
            config_file=self.project_path / "pyproject.toml",
            package_name="fake_package_name",
            project_name="fake_project_name",
            kedro_init_version=kedro_version,
            project_path=self.project_path,
            add_ons=None,
        )
        assert actual == expected

    def test_toml_file_with_extra_keys(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": kedro_version,
                    "unexpected_key": "hello",
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)
        pattern = (
            "Found unexpected keys in 'pyproject.toml'. Make sure it "
            "only contains the following keys: ['package_name', "
            "'project_name', 'kedro_init_version', 'source_dir']."
        )

        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            _get_project_metadata(self.project_path)

    def test_toml_file_has_missing_mandatory_keys(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "kedro_init_version": kedro_version,
                    "unexpected_key": "hello",
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)
        pattern = (
            "Missing required keys ['package_name', 'project_name'] "
            "from 'pyproject.toml'."
        )

        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            _get_project_metadata(self.project_path)

    def test_toml_file_without_kedro_section(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("anyconfig.load", return_value={})

        pattern = "There's no '[tool.kedro]' section in the 'pyproject.toml'."

        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            _get_project_metadata(self.project_path)

    def test_source_dir_specified_in_toml(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        source_dir = "test_dir"
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "source_dir": source_dir,
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": kedro_version,
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)

        project_metadata = _get_project_metadata(self.project_path)

        assert project_metadata.source_dir == self.project_path / source_dir

    @pytest.mark.parametrize(
        "invalid_version", ["0.13.0", "10.0", "101.1", "100.0", "-0"]
    )
    def test_invalid_version(self, invalid_version, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "source_dir": "source_dir",
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": invalid_version,
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)

        pattern = (
            f"Your Kedro project version {invalid_version} does not match "
            f"Kedro package version {kedro_version} you are running."
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            _get_project_metadata(self.project_path)

    # Temporary test for coverage to be removed in 0.19.0 when project_version is removed
    @pytest.mark.parametrize(
        "invalid_version", ["0.13.0", "10.0", "101.1", "100.0", "-0"]
    )
    def test_invalid_version_for_kedro_version(self, invalid_version, mocker):
        mocker.patch.object(Path, "is_file", return_value=True)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "source_dir": "source_dir",
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": invalid_version,
                }
            }
        }
        mocker.patch("anyconfig.load", return_value=pyproject_toml_payload)

        pattern = (
            f"Your Kedro project version {invalid_version} does not match "
            f"Kedro package version {kedro_version} you are running."
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            _get_project_metadata(self.project_path)


class TestValidateSourcePath:
    @pytest.mark.parametrize(
        "source_dir", [".", "src", "./src", "src/nested", "src/nested/nested"]
    )
    def test_valid_source_path(self, tmp_path, source_dir):
        source_path = (tmp_path / source_dir).resolve()
        source_path.mkdir(parents=True, exist_ok=True)
        _validate_source_path(source_path, tmp_path.resolve())

    @pytest.mark.parametrize("source_dir", ["..", "src/../..", "~"])
    def test_invalid_source_path(self, tmp_path, source_dir):
        source_dir = Path(source_dir).expanduser()
        source_path = (tmp_path / source_dir).resolve()
        source_path.mkdir(parents=True, exist_ok=True)

        pattern = re.escape(
            f"Source path '{source_path}' has to be relative to your project root "
            f"'{tmp_path.resolve()}'"
        )
        with pytest.raises(ValueError, match=pattern):
            _validate_source_path(source_path, tmp_path.resolve())

    def test_non_existent_source_path(self, tmp_path):
        source_path = (tmp_path / "non_existent").resolve()

        pattern = re.escape(f"Source path '{source_path}' cannot be found.")
        with pytest.raises(NotADirectoryError, match=pattern):
            _validate_source_path(source_path, tmp_path.resolve())


class TestBootstrapProject:
    def test_bootstrap_project(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PYTHONPATH", raising=False)
        pyproject_toml_payload = {
            "tool": {
                "kedro": {
                    "package_name": "fake_package_name",
                    "project_name": "fake_project_name",
                    "kedro_init_version": kedro_version,
                }
            }
        }
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(toml.dumps(pyproject_toml_payload))
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        result = bootstrap_project(tmp_path)

        expected_metadata = {
            "config_file": pyproject_toml,
            "package_name": "fake_package_name",
            "project_name": "fake_project_name",
            "project_path": tmp_path,
            "kedro_init_version": kedro_version,
            "source_dir": src_dir,
            "add_ons": None,
        }
        assert result == ProjectMetadata(**expected_metadata)
        assert str(src_dir) in sys.path[0]
        assert os.environ["PYTHONPATH"] == str(src_dir)
