import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from kedro_datasets.pandas import CSVDataset
from pandas import DataFrame

from kedro.framework.cli.pipeline import _sync_dirs
from kedro.framework.project import settings
from kedro.framework.session import KedroSession

PACKAGE_NAME = "dummy_package"
PIPELINE_NAME = "my_pipeline"


@pytest.fixture(params=["base"])
def make_pipelines(request, fake_repo_path, fake_package_path, mocker):
    source_path = fake_package_path / "pipelines" / PIPELINE_NAME
    tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
    conf_path = fake_repo_path / settings.CONF_SOURCE / request.param
    # old conf structure for 'pipeline delete' command backward compatibility
    old_conf_path = conf_path / "parameters"

    for path in (source_path, tests_path, conf_path, old_conf_path):
        path.mkdir(parents=True, exist_ok=True)

    (tests_path / "test_pipe.py").touch()
    (source_path / "pipe.py").touch()
    (conf_path / f"parameters_{PIPELINE_NAME}.yml").touch()
    (old_conf_path / f"{PIPELINE_NAME}.yml").touch()

    yield
    mocker.stopall()
    shutil.rmtree(str(source_path), ignore_errors=True)
    shutil.rmtree(str(tests_path), ignore_errors=True)
    shutil.rmtree(str(conf_path), ignore_errors=True)


LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestPipelineCreateCommand:
    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline(
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

        # pipeline
        assert f"Creating the pipeline '{PIPELINE_NAME}': OK" in result.output
        assert f"Location: '{pipelines_dir / PIPELINE_NAME}'" in result.output
        assert f"Pipeline '{PIPELINE_NAME}' was successfully created." in result.output

        # config
        conf_env = env or "base"
        conf_dir = (fake_repo_path / settings.CONF_SOURCE / conf_env).resolve()
        actual_configs = list(conf_dir.glob(f"**/*{PIPELINE_NAME}.yml"))
        expected_configs = [conf_dir / f"parameters_{PIPELINE_NAME}.yml"]
        assert actual_configs == expected_configs

        # tests
        test_dir = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        expected_files = {"__init__.py", "test_pipeline.py"}
        actual_files = {f.name for f in test_dir.iterdir()}
        assert actual_files == expected_files

    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline_template(
        self,
        fake_repo_path,
        fake_project_cli,
        fake_metadata,
        env,
        fake_package_path,
        fake_local_template_dir,
    ):
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        assert not (pipelines_dir / PIPELINE_NAME).exists()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        cmd += ["-e", env] if env else []
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)

        assert (
            f"Using pipeline template at: '{fake_repo_path / 'templates'}"
            in result.output
        )
        assert f"Creating the pipeline '{PIPELINE_NAME}': OK" in result.output
        assert f"Location: '{pipelines_dir / PIPELINE_NAME}'" in result.output
        assert f"Pipeline '{PIPELINE_NAME}' was successfully created." in result.output

        # Dummy pipeline rendered correctly
        assert (pipelines_dir / PIPELINE_NAME / f"pipeline_{PIPELINE_NAME}.py").exists()

        assert result.exit_code == 0

    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline_template_command_line_override(
        self,
        fake_repo_path,
        fake_project_cli,
        fake_metadata,
        env,
        fake_package_path,
        fake_local_template_dir,
    ):
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        assert not (pipelines_dir / PIPELINE_NAME).exists()

        # Rename the local template dir to something else so we know the command line flag is taking precedence
        try:
            # Can skip if already there but copytree has a dirs_exist_ok flag in >python 3.8 only
            shutil.copytree(fake_local_template_dir, fake_repo_path / "local_templates")
        except FileExistsError:
            pass

        cmd = ["pipeline", "create", PIPELINE_NAME]
        cmd += ["-t", str(fake_repo_path / "local_templates/pipeline")]
        cmd += ["-e", env] if env else []
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)

        assert (
            f"Using pipeline template at: '{fake_repo_path / 'local_templates'}"
            in result.output
        )
        assert f"Creating the pipeline '{PIPELINE_NAME}': OK" in result.output
        assert f"Location: '{pipelines_dir / PIPELINE_NAME}'" in result.output
        assert f"Pipeline '{PIPELINE_NAME}' was successfully created." in result.output

        # Dummy pipeline rendered correctly
        assert (pipelines_dir / PIPELINE_NAME / f"pipeline_{PIPELINE_NAME}.py").exists()

        assert result.exit_code == 0

    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline_skip_config(
        self, fake_repo_path, fake_project_cli, fake_metadata, env
    ):
        """Test creation of a pipeline with no config"""

        cmd = ["pipeline", "create", "--skip-config", PIPELINE_NAME]
        cmd += ["-e", env] if env else []

        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)
        assert result.exit_code == 0
        assert f"Creating the pipeline '{PIPELINE_NAME}': OK" in result.output
        assert f"Pipeline '{PIPELINE_NAME}' was successfully created." in result.output

        conf_dirs = list((fake_repo_path / settings.CONF_SOURCE).rglob(PIPELINE_NAME))
        assert not conf_dirs  # no configs created for the pipeline

        test_dir = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        assert test_dir.is_dir()

    def test_catalog_and_params(
        self, fake_repo_path, fake_project_cli, fake_metadata, fake_package_path
    ):
        """Test that catalog and parameter configs generated in pipeline
        sections propagate into the context"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)
        assert result.exit_code == 0

        # write pipeline catalog
        conf_dir = fake_repo_path / settings.CONF_SOURCE / "base"
        catalog_dict = {
            "ds_from_pipeline": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/iris.csv",
            }
        }
        catalog_file = conf_dir / f"catalog_{PIPELINE_NAME}.yml"
        with catalog_file.open("w") as f:
            yaml.dump(catalog_dict, f)

        # write pipeline parameters
        params_file = conf_dir / f"parameters_{PIPELINE_NAME}.yml"
        assert params_file.is_file()
        params_dict = {"params_from_pipeline": {"p1": [1, 2, 3], "p2": None}}
        with params_file.open("w") as f:
            yaml.dump(params_dict, f)

        with KedroSession.create(PACKAGE_NAME) as session:
            ctx = session.load_context()
        assert isinstance(ctx.catalog._datasets["ds_from_pipeline"], CSVDataset)
        assert isinstance(ctx.catalog.load("ds_from_pipeline"), DataFrame)
        assert ctx.params["params_from_pipeline"] == params_dict["params_from_pipeline"]

    def test_skip_copy(self, fake_repo_path, fake_project_cli, fake_metadata):
        """Test skipping the copy of conf and test files if those already exist"""
        # create catalog and parameter files
        for dirname in ("catalog", "parameters"):
            path = (
                fake_repo_path
                / settings.CONF_SOURCE
                / "base"
                / f"{dirname}_{PIPELINE_NAME}.yml"
            )
            path.parent.mkdir(exist_ok=True)
            path.touch()

        # create __init__.py in tests
        tests_init = (
            fake_repo_path
            / "src"
            / "tests"
            / "pipelines"
            / PIPELINE_NAME
            / "__init__.py"
        )
        tests_init.parent.mkdir(parents=True)
        tests_init.touch()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)

        assert result.exit_code == 0
        assert "__init__.py': SKIPPED" in result.output
        assert f"parameters_{PIPELINE_NAME}.yml': SKIPPED" in result.output
        assert result.output.count("SKIPPED") == 2  # only 2 files skipped

    def test_failed_copy(
        self, fake_project_cli, fake_metadata, fake_package_path, mocker
    ):
        """Test the error if copying some file fails"""
        error = Exception("Mock exception")
        mocked_copy = mocker.patch("shutil.copyfile", side_effect=error)

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)
        mocked_copy.assert_called_once()
        assert result.exit_code
        assert result.output.count("FAILED") == 1
        assert result.exception is error

        # but the pipeline is created anyways
        pipelines_dir = fake_package_path / "pipelines"
        assert (pipelines_dir / PIPELINE_NAME / "pipeline.py").is_file()

    def test_no_pipeline_arg_error(
        self, fake_project_cli, fake_metadata, fake_package_path
    ):
        """Test the error when no pipeline name was provided"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create"], obj=fake_metadata
        )
        assert result.exit_code
        assert "Missing argument 'NAME'" in result.output

    @pytest.mark.parametrize(
        "bad_name,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_bad_pipeline_name(
        self, fake_project_cli, fake_metadata, bad_name, error_message
    ):
        """Test error message when bad pipeline name was provided"""
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", bad_name], obj=fake_metadata
        )
        assert result.exit_code
        assert error_message in result.output

    def test_duplicate_pipeline_name(
        self, fake_project_cli, fake_metadata, fake_package_path
    ):
        """Test error when attempting to create pipelines with duplicate names"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        first = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)
        assert first.exit_code == 0

        second = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)
        assert second.exit_code
        assert f"Creating the pipeline '{PIPELINE_NAME}': FAILED" in second.output
        assert "directory already exists" in second.output

    def test_bad_env(self, fake_project_cli, fake_metadata):
        """Test error when provided conf environment does not exist"""
        env = "no_such_env"
        cmd = ["pipeline", "create", "-e", env, PIPELINE_NAME]
        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)
        assert result.exit_code
        assert f"Unable to locate environment '{env}'" in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "make_pipelines")
class TestPipelineDeleteCommand:
    @pytest.mark.parametrize(
        "make_pipelines,env,expected_conf",
        [("base", None, "base"), ("local", "local", "local")],
        indirect=["make_pipelines"],
    )
    def test_delete_pipeline(
        self,
        env,
        expected_conf,
        fake_repo_path,
        fake_project_cli,
        fake_metadata,
        fake_package_path,
    ):
        options = ["--env", env] if env else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", "-y", PIPELINE_NAME, *options],
            obj=fake_metadata,
        )

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        conf_path = fake_repo_path / settings.CONF_SOURCE / expected_conf
        params_path = conf_path / f"parameters_{PIPELINE_NAME}.yml"
        # old params structure for 'pipeline delete' command backward compatibility
        old_params_path = conf_path / "parameters" / f"{PIPELINE_NAME}.yml"

        assert f"Deleting '{source_path}': OK" in result.output
        assert f"Deleting '{tests_path}': OK" in result.output
        assert f"Deleting '{params_path}': OK" in result.output
        assert f"Deleting '{old_params_path}': OK" in result.output

        assert f"Pipeline '{PIPELINE_NAME}' was successfully deleted." in result.output
        assert (
            f"If you added the pipeline '{PIPELINE_NAME}' to 'register_pipelines()' in "
            f"""'{fake_package_path / "pipeline_registry.py"}', you will need to remove it."""
        ) in result.output

        assert not source_path.exists()
        assert not tests_path.exists()
        assert not params_path.exists()
        assert not params_path.exists()

    def test_delete_pipeline_skip(
        self, fake_repo_path, fake_project_cli, fake_metadata, fake_package_path
    ):
        """Tests that delete pipeline handles missing or already deleted files gracefully"""
        source_path = fake_package_path / "pipelines" / PIPELINE_NAME

        shutil.rmtree(str(source_path))

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", "-y", PIPELINE_NAME],
            obj=fake_metadata,
        )
        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_SOURCE
            / "base"
            / f"parameters_{PIPELINE_NAME}.yml"
        )

        assert f"Deleting '{source_path}'" not in result.output
        assert f"Deleting '{tests_path}': OK" in result.output
        assert f"Deleting '{params_path}': OK" in result.output

        assert f"Pipeline '{PIPELINE_NAME}' was successfully deleted." in result.output
        assert (
            f"If you added the pipeline '{PIPELINE_NAME}' to 'register_pipelines()' in "
            f"""'{fake_package_path / "pipeline_registry.py"}', you will need to remove it."""
        ) in result.output

        assert not source_path.exists()
        assert not tests_path.exists()
        assert not params_path.exists()

    def test_delete_pipeline_fail(
        self, fake_project_cli, fake_metadata, fake_package_path, mocker
    ):
        source_path = fake_package_path / "pipelines" / PIPELINE_NAME

        mocker.patch(
            "kedro.framework.cli.pipeline.shutil.rmtree",
            side_effect=PermissionError("permission"),
        )
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", "-y", PIPELINE_NAME],
            obj=fake_metadata,
        )

        assert result.exit_code, result.output
        assert f"Deleting '{source_path}': FAILED" in result.output

    @pytest.mark.parametrize(
        "bad_name,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_bad_pipeline_name(
        self, fake_project_cli, fake_metadata, bad_name, error_message
    ):
        """Test error message when bad pipeline name was provided."""
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "delete", "-y", bad_name], obj=fake_metadata
        )
        assert result.exit_code
        assert error_message in result.output

    def test_pipeline_not_found(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", "-y", "non_existent"],
            obj=fake_metadata,
        )
        assert result.exit_code
        assert "Pipeline 'non_existent' not found." in result.output

    def test_bad_env(self, fake_project_cli, fake_metadata):
        """Test error when provided conf environment does not exist."""
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", "-y", "-e", "invalid_env", PIPELINE_NAME],
            obj=fake_metadata,
        )
        assert result.exit_code
        assert "Unable to locate environment 'invalid_env'" in result.output

    @pytest.mark.parametrize("input_", ["n", "N", "random"])
    def test_pipeline_delete_confirmation(
        self, fake_repo_path, fake_project_cli, fake_metadata, fake_package_path, input_
    ):
        """Test that user confirmation of deletion works"""
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", PIPELINE_NAME],
            input=input_,
            obj=fake_metadata,
        )

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_SOURCE
            / "base"
            / f"parameters_{PIPELINE_NAME}.yml"
        )

        assert "The following paths will be removed:" in result.output
        assert str(source_path) in result.output
        assert str(tests_path) in result.output
        assert str(params_path) in result.output

        assert (
            f"Are you sure you want to delete pipeline '{PIPELINE_NAME}'"
            in result.output
        )
        assert "Deletion aborted!" in result.output

        assert source_path.is_dir()
        assert tests_path.is_dir()
        assert params_path.is_file()

    @pytest.mark.parametrize("input_", ["n", "N", "random"])
    def test_pipeline_delete_confirmation_skip(
        self, fake_repo_path, fake_project_cli, fake_metadata, fake_package_path, input_
    ):
        """Test that user confirmation of deletion works when
        some of the files are missing or already deleted
        """

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        shutil.rmtree(str(source_path))
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "delete", PIPELINE_NAME],
            input=input_,
            obj=fake_metadata,
        )

        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_SOURCE
            / "base"
            / f"parameters_{PIPELINE_NAME}.yml"
        )

        assert "The following paths will be removed:" in result.output
        assert str(source_path) not in result.output
        assert str(tests_path) in result.output
        assert str(params_path) in result.output

        assert (
            f"Are you sure you want to delete pipeline '{PIPELINE_NAME}'"
            in result.output
        )
        assert "Deletion aborted!" in result.output

        assert tests_path.is_dir()
        assert params_path.is_file()


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
