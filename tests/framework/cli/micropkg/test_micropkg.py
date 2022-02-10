from pathlib import Path

import pytest
from click.testing import CliRunner

from kedro.framework.cli.micropkg import _sync_dirs
from kedro.framework.project import settings

PIPELINE_NAME = "my_pipeline"


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelineCreateCommand:
    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline(  # pylint: disable=too-many-locals
        self, fake_repo_path, fake_project_cli, fake_metadata, env, fake_package_path
    ):
        """Test creation of a pipeline"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        assert not (pipelines_dir / PIPELINE_NAME).exists()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        cmd += ["-e", env] if env else []
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)

        assert result.exit_code == 0
        assert (
            f"To be able to run the pipeline `{PIPELINE_NAME}`, you will need "
            f"to add it to `register_pipelines()`" in result.output
        )

        # pipeline
        assert f"Creating the pipeline `{PIPELINE_NAME}`: OK" in result.output
        assert f"Location: `{pipelines_dir / PIPELINE_NAME}`" in result.output
        assert f"Pipeline `{PIPELINE_NAME}` was successfully created." in result.output

        # config
        conf_env = env or "base"
        conf_dir = (fake_repo_path / settings.CONF_ROOT / conf_env).resolve()
        actual_configs = list(conf_dir.glob(f"**/{PIPELINE_NAME}.yml"))
        expected_configs = [conf_dir / "parameters" / f"{PIPELINE_NAME}.yml"]
        assert actual_configs == expected_configs

        # tests
        test_dir = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        expected_files = {"__init__.py", "test_pipeline.py"}
        actual_files = {f.name for f in test_dir.iterdir()}
        assert actual_files == expected_files


class TestSyncDirs:
    @pytest.fixture(autouse=True)
    def mock_click(self, mocker):
        mocker.patch("click.secho")

    @pytest.fixture
    def source(self, tmp_path) -> Path:
        source_dir = Path(tmp_path) / "source"
        source_dir.mkdir()
        (source_dir / "existing").mkdir()
        (source_dir / "existing" / "source_file").touch()
        (source_dir / "existing" / "common").write_text("source", encoding="utf-8")
        (source_dir / "new").mkdir()
        (source_dir / "new" / "source_file").touch()
        return source_dir

    def test_sync_target_exists(self, source, tmp_path):
        """Test _sync_dirs utility function if target exists."""
        target = Path(tmp_path) / "target"
        target.mkdir()
        (target / "existing").mkdir()
        (target / "existing" / "target_file").touch()
        (target / "existing" / "common").write_text("target", encoding="utf-8")

        _sync_dirs(source, target)

        assert (source / "existing" / "source_file").is_file()
        assert (source / "existing" / "common").read_text() == "source"
        assert not (source / "existing" / "target_file").exists()
        assert (source / "new" / "source_file").is_file()

        assert (target / "existing" / "source_file").is_file()
        assert (target / "existing" / "common").read_text(encoding="utf-8") == "target"
        assert (target / "existing" / "target_file").exists()
        assert (target / "new" / "source_file").is_file()

    def test_sync_no_target(self, source, tmp_path):
        """Test _sync_dirs utility function if target doesn't exist."""
        target = Path(tmp_path) / "target"

        _sync_dirs(source, target)

        assert (source / "existing" / "source_file").is_file()
        assert (source / "existing" / "common").read_text() == "source"
        assert not (source / "existing" / "target_file").exists()
        assert (source / "new" / "source_file").is_file()

        assert (target / "existing" / "source_file").is_file()
        assert (target / "existing" / "common").read_text(encoding="utf-8") == "source"
        assert not (target / "existing" / "target_file").exists()
        assert (target / "new" / "source_file").is_file()
