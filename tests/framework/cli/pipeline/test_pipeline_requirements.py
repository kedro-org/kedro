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
import pkg_resources
import pytest
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_wheel_name

PIPELINE_NAME = "my_pipeline"

# Inspired by test cases given in https://www.python.org/dev/peps/pep-0508/.
# These are all valid requirement specifications that can be used in both
# requirements.txt and in METADATA Requires-Dist.
VALID_REQUIREMENTS = """A
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
            ["pipeline", "package", PIPELINE_NAME],
            obj=metadata,
        )
        assert result.exit_code == 0

    def call_pipeline_delete(self, cli, metadata):
        result = CliRunner().invoke(
            cli, ["pipeline", "delete", "-y", PIPELINE_NAME], obj=metadata
        )
        assert result.exit_code == 0

    def call_pipeline_pull(self, cli, metadata, repo_path):
        wheel_file = (
            repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )
        assert wheel_file.is_file()

        result = CliRunner().invoke(
            cli,
            ["pipeline", "pull", str(wheel_file)],
            obj=metadata,
        )
        assert result.exit_code == 0

    def test_existing_project_requirements_txt(
        self, fake_project_cli, fake_metadata, fake_package_path, fake_repo_path
    ):
        """Pipeline requirements.txt and project requirements.txt, but no project
        requirements.in."""
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_requirements_txt = (
            fake_package_path / "pipelines" / PIPELINE_NAME / "requirements.txt"
        )
        pipeline_requirements_txt.write_text(VALID_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        packaged_requirements = pkg_resources.parse_requirements(VALID_REQUIREMENTS)
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        pulled_requirements = pkg_resources.parse_requirements(
            project_requirements_in.read_text()
        )
        # Packaged requirements expected to be a subset of pulled requirements due to
        # default project level requirements.txt (e.g. black, flake8), which should be
        # preserved
        assert set(packaged_requirements) <= set(pulled_requirements)

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
        pipeline_requirements_txt.write_text(VALID_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        packaged_requirements = pkg_resources.parse_requirements(VALID_REQUIREMENTS)
        existing_requirements = pkg_resources.parse_requirements(initial_dependency)
        pulled_requirements = pkg_resources.parse_requirements(
            project_requirements_in.read_text()
        )
        # Requirements after pulling a pipeline expected to be the union of
        # requirements packaged and requirements already existing at project level
        assert set(pulled_requirements) == set(packaged_requirements) | set(
            existing_requirements
        )

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

        pipeline_requirements_txt.write_text(VALID_REQUIREMENTS)
        packaged_requirements = pkg_resources.parse_requirements(VALID_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        project_requirements_in = fake_repo_path / "src" / "requirements.in"

        assert not project_requirements_txt.exists()
        assert project_requirements_in.exists()
        pulled_requirements = pkg_resources.parse_requirements(
            project_requirements_in.read_text()
        )
        assert set(packaged_requirements) == set(pulled_requirements)

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
        pipeline_requirements_txt.write_text(VALID_REQUIREMENTS)
        project_requirements_txt.write_text(VALID_REQUIREMENTS)

        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)
        self.call_pipeline_pull(fake_project_cli, fake_metadata, fake_repo_path)

        # requirements.txt expected to be copied into requirements.in without any
        # addition
        project_requirements_in = fake_repo_path / "src" / "requirements.in"
        assert project_requirements_in.exists()
        assert project_requirements_in.read_text() == VALID_REQUIREMENTS

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

    @pytest.mark.parametrize(
        "requirement",
        [
            "--extra-index-url https://this.wont.work",
            "-r other_requirements.txt",
            "./path/to/package.whl",
            "http://some.website.com/package.whl",
        ],
    )
    def test_invalid_requirements(
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
            ["pipeline", "package", PIPELINE_NAME],
            obj=fake_metadata,
        )
        assert result.exit_code == 1
        assert "InvalidRequirement: Parse error" in result.output
