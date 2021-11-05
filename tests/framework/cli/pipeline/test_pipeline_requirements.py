import pkg_resources
import pytest
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_wheel_name, _safe_parse_requirements
from kedro.framework.cli.pipeline import _get_sdist_name

PIPELINE_NAME = "my_pipeline"

# Inspired by test cases given in https://www.python.org/dev/peps/pep-0508/.
# These are all valid requirement specifications that can be used in both
# requirements.txt and in METADATA Requires-Dist.
SIMPLE_REQUIREMENTS = """A
A.B-C_D
aa
name
name<=1
name>=3
name>=3,<2
name==1.2.3
name!=1.2.3 # inline comment
# whole line comment
name@http://foo.com
name [fred,bar] @ http://foo.com ; python_version=='2.7'
name[quux, strange];python_version<'2.7' and platform_version=='2'
name; os_name=='a' or os_name=='b'
requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"
pip @ https://github.com/pypa/pip/archive/1.3.1.zip#sha1=da9234ees
"""

# These requirements can be used in requirements.txt but not in METADATA Requires-Dist.
# They cannot be parsed by pkg_resources.
COMPLEX_REQUIREMENTS = """--extra-index-url https://this.wont.work
-r other_requirements.txt
./path/to/package.whl
http://some.website.com/package.whl
"""


@pytest.mark.usefixtures("chdir_to_dummy_project", "cleanup_dist")
class TestPipelineRequirements:
    """Many of these tests follow the pattern:
    - create a pipeline with some sort of requirements.txt
    - package the pipeline
    - delete the pipeline and pull in the packaged one
    - assert the project's modified requirements.in is as expected
    """

    def call_pipeline_create(self, cli, metadata):
        result = CliRunner().invoke(
            cli, ["pipeline", "create", PIPELINE_NAME], obj=metadata
        )
        assert result.exit_code == 0

    def call_pipeline_package(self, cli, metadata):
        result = CliRunner().invoke(
            cli,
            ["pipeline", "package", f"pipelines.{PIPELINE_NAME}"],
            obj=metadata,
        )
        assert result.exit_code == 0

    def call_pipeline_delete(self, cli, metadata):
        result = CliRunner().invoke(
            cli, ["pipeline", "delete", "-y", PIPELINE_NAME], obj=metadata
        )
        assert result.exit_code == 0

    def call_pipeline_pull(self, cli, metadata, repo_path):
        sdist_file = (
            repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )
        assert sdist_file.is_file()

        result = CliRunner().invoke(
            cli,
            ["pipeline", "pull", str(sdist_file)],
            obj=metadata,
        )
        assert result.exit_code == 0

    def _remove_spaces_from_reqs(self, requirements_file):
        return [str(r).replace(" ", "") for r in requirements_file]

    def test_existing_complex_project_requirements_txt(
        self, fake_project_cli, fake_metadata, fake_package_path, fake_repo_path
    ):
        """Pipeline requirements.txt and project requirements.txt, but no project
        requirements.in."""
        project_requirements_txt = fake_repo_path / "src" / "requirements.txt"
        with open(project_requirements_txt, "a", encoding="utf-8") as file:
            file.write(COMPLEX_REQUIREMENTS)
        existing_requirements = _safe_parse_requirements(
            project_requirements_txt.read_text()
        )

        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.write_text(SIMPLE_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        packaged_requirements = _safe_parse_requirements(SIMPLE_REQUIREMENTS)
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        pulled_requirements = _safe_parse_requirements(
            project_requirements_in.read_text()
        )
        # requirements.in afterwards should be the requirements that already existed in
        # project requirements.txt + those pulled in from pipeline requirements.txt.
        # Unparseable COMPLEX_REQUIREMENTS should still be there.
        assert pulled_requirements == existing_requirements | packaged_requirements
        assert COMPLEX_REQUIREMENTS in project_requirements_in.read_text()

    def test_existing_project_requirements_txt(
        self, fake_project_cli, fake_metadata, fake_package_path, fake_repo_path
    ):
        """Pipeline requirements.txt and project requirements.txt, but no project
        requirements.in."""
        project_requirements_txt = fake_repo_path / "src" / "requirements.txt"
        existing_requirements = _safe_parse_requirements(
            project_requirements_txt.read_text()
        )

        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.write_text(SIMPLE_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        packaged_requirements = _safe_parse_requirements(SIMPLE_REQUIREMENTS)
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        pulled_requirements = _safe_parse_requirements(
            project_requirements_in.read_text()
        )
        # requirements.in afterwards should be the requirements that already existed in
        # project requirements.txt + those pulled in from pipeline requirements.txt.
        assert pulled_requirements == existing_requirements | packaged_requirements

    def test_existing_complex_project_requirements_in(
        self, fake_project_cli, fake_metadata, fake_package_path, fake_repo_path
    ):
        """Pipeline requirements.txt and a pre-existing project requirements.in."""
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        project_requirements_in.write_text(COMPLEX_REQUIREMENTS)
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.write_text(SIMPLE_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        packaged_requirements = _safe_parse_requirements(SIMPLE_REQUIREMENTS)
        existing_requirements = _safe_parse_requirements(COMPLEX_REQUIREMENTS)
        pulled_requirements = _safe_parse_requirements(
            project_requirements_in.read_text()
        )
        # requirements.in afterwards should be the requirements that already existed in
        # project requirements.txt + those pulled in from pipeline requirements.txt.
        # Unparseable COMPLEX_REQUIREMENTS should still be there.
        assert pulled_requirements == existing_requirements | packaged_requirements
        assert COMPLEX_REQUIREMENTS in project_requirements_in.read_text()

    def test_existing_project_requirements_in(
        self, fake_project_cli, fake_metadata, fake_package_path, fake_repo_path
    ):
        """Pipeline requirements.txt and a pre-existing project requirements.in."""
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        initial_dependency = "some_package==0.1.0"
        project_requirements_in.write_text(initial_dependency)
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.write_text(SIMPLE_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        packaged_requirements = _safe_parse_requirements(SIMPLE_REQUIREMENTS)
        existing_requirements = _safe_parse_requirements(initial_dependency)
        pulled_requirements = _safe_parse_requirements(
            project_requirements_in.read_text()
        )
        # requirements.in afterwards should be the requirements that already existed in
        # project requirements.txt + those pulled in from pipeline requirements.txt.
        assert pulled_requirements == existing_requirements | packaged_requirements

    def test_missing_project_requirements_in_and_txt(
        self,
        fake_project_cli,
        fake_metadata,
        fake_package_path,
        fake_repo_path,
    ):
        """Pipeline requirements.txt without requirements.in or requirements.txt at
        project level."""
        # Remove project requirements.txt
        project_requirements_txt = fake_repo_path / "src" / "requirements.txt"
        project_requirements_txt.unlink()

        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )

        pipeline_requirements_txt.write_text(SIMPLE_REQUIREMENTS)
        packaged_requirements = _safe_parse_requirements(SIMPLE_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        project_requirements_in = fake_repo_path / "src" / "requirements.in"

        assert not project_requirements_txt.exists()
        assert project_requirements_in.exists()
        pulled_requirements = _safe_parse_requirements(
            project_requirements_in.read_text()
        )
        assert packaged_requirements == pulled_requirements

    def test_no_requirements(
        self,
        fake_project_cli,
        fake_metadata,
        fake_repo_path,
    ):
        """No pipeline requirements.txt, and also no requirements.in or requirements.txt
        at project level."""
        # Remove project requirements.txt
        project_requirements_txt = fake_repo_path / "src" / "requirements.txt"
        project_requirements_txt.unlink()

        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        project_requirements_txt = fake_repo_path / "src" / "requirements.txt"
        assert not project_requirements_txt.exists()
        assert not project_requirements_in.exists()

    def test_all_requirements_already_covered(
        self, fake_project_cli, fake_metadata, fake_repo_path, fake_package_path
    ):
        """All requirements from pipeline requirements.txt already exist at project
        level requirements.txt."""
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        project_requirements_txt = fake_repo_path / "src" / "requirements.txt"
        pipeline_requirements_txt.write_text(SIMPLE_REQUIREMENTS)
        project_requirements_txt.write_text(SIMPLE_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        # requirements.txt expected to be copied into requirements.in without any
        # addition
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        assert project_requirements_in.exists()
        assert project_requirements_in.read_text() == SIMPLE_REQUIREMENTS

    def test_no_pipeline_requirements_txt(
        self, fake_project_cli, fake_metadata, fake_repo_path
    ):
        """No pipeline requirements.txt and no project requirements.in does not
        create project requirements.in."""
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        assert not project_requirements_in.exists()

    def test_empty_pipeline_requirements_txt(
        self, fake_project_cli, fake_metadata, fake_package_path, fake_repo_path
    ):
        """Empty pipeline requirements.txt and no project requirements.in does not
        create project requirements.in."""
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.touch()
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        assert not project_requirements_in.exists()

    @pytest.mark.parametrize("requirement", COMPLEX_REQUIREMENTS.splitlines())
    def test_complex_requirements(
        self, requirement, fake_project_cli, fake_metadata, fake_package_path
    ):
        """Options that are valid in requirements.txt but cannot be packaged using
        setup.py."""
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.write_text(requirement)

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", f"pipelines.{PIPELINE_NAME}"],
            obj=fake_metadata,
        )
        assert result.exit_code == 1
        assert "InvalidRequirement: Parse error" in result.output
