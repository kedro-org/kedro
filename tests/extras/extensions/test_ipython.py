# Copyright 2020 QuantumBlack Visual Analytics Limited
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
# pylint: disable=import-outside-toplevel,reimported
import pytest

from kedro.extras.extensions.ipython import (
    init_kedro,
    load_ipython_extension,
    load_kedro_objects,
)
from kedro.framework.project import ProjectMetadata
from kedro.framework.session.session import _deactivate_session


@pytest.fixture(autouse=True)
def project_path(mocker, tmp_path):
    path = tmp_path
    mocker.patch("kedro.extras.extensions.ipython.project_path", path)


@pytest.fixture(autouse=True)
def cleanup_session():
    yield
    _deactivate_session()


class TestInitKedro:
    def test_init_kedro(self, tmp_path, caplog):
        from kedro.extras.extensions.ipython import project_path

        assert project_path == tmp_path

        kedro_path = tmp_path / "here"
        init_kedro(str(kedro_path))
        expected_path = kedro_path.expanduser().resolve()
        expected_message = f"Updated path to Kedro project: {expected_path}"

        log_messages = [record.getMessage() for record in caplog.records]
        assert expected_message in log_messages
        from kedro.extras.extensions.ipython import project_path

        # make sure global variable updated
        assert project_path == expected_path

    def test_init_kedro_no_path(self, tmp_path, caplog):
        from kedro.extras.extensions.ipython import project_path

        assert project_path == tmp_path

        init_kedro()
        expected_message = f"No path argument was provided. Using: {tmp_path}"

        log_messages = [record.getMessage() for record in caplog.records]
        assert expected_message in log_messages
        from kedro.extras.extensions.ipython import project_path

        # make sure global variable stayed the same
        assert project_path == tmp_path


class TestLoadKedroObjects:
    def test_load_kedro_objects(self, tmp_path, mocker):
        fake_metadata = ProjectMetadata(
            source_dir=tmp_path / "src",  # default
            config_file=tmp_path / "pyproject.toml",
            package_name="fake_package_name",
            project_name="fake_project_name",
            project_version="0.1",
        )
        mocker.patch(
            "kedro.framework.project.metadata._get_project_metadata",
            return_value=fake_metadata,
        )
        mocker.patch(
            "kedro.framework.session.session._get_project_metadata",
            return_value=fake_metadata,
        )
        mocker.patch("kedro.framework.cli.utils._add_src_to_path")
        mock_line_magic = mocker.MagicMock()
        mock_line_magic.__name__ = "abc"
        mocker.patch(
            "kedro.framework.cli.load_entry_points", return_value=[mock_line_magic]
        )
        mock_register_line_magic = mocker.patch(
            "kedro.extras.extensions.ipython.register_line_magic"
        )
        mock_context = mocker.patch("kedro.framework.session.KedroSession.load_context")
        mock_get_settings = mocker.patch(
            "kedro.framework.session.session._get_project_settings", return_value={}
        )
        mock_ipython = mocker.patch("kedro.extras.extensions.ipython.get_ipython")

        load_kedro_objects(tmp_path)

        mock_ipython().push.assert_called_once_with(
            variables={
                "context": mock_context(),
                "catalog": mock_context().catalog,
                "session": mocker.ANY,
            }
        )
        assert mock_register_line_magic.call_count == 1
        mock_get_settings.assert_called_once_with(
            fake_metadata.package_name, "SESSION_STORE", {}
        )

    def test_load_kedro_objects_not_in_kedro_project(self, tmp_path, mocker):
        mocker.patch(
            "kedro.framework.project.metadata._get_project_metadata",
            side_effect=[RuntimeError],
        )
        mock_ipython = mocker.patch("kedro.extras.extensions.ipython.get_ipython")

        with pytest.raises(RuntimeError):
            load_kedro_objects(tmp_path)
        assert not mock_ipython().called
        assert not mock_ipython().push.called


class TestLoadIPythonExtension:
    @pytest.mark.parametrize(
        "error,expected_log_message",
        [
            (
                ImportError,
                "Kedro appears not to be installed in your current environment.",
            ),
            (
                RuntimeError,
                "Could not register Kedro extension. Make sure you're in a valid Kedro project.",
            ),
        ],
    )
    def test_load_extension_not_in_kedro_env_or_project(
        self, error, expected_log_message, mocker, caplog
    ):
        mocker.patch(
            "kedro.framework.project.metadata._get_project_metadata",
            side_effect=[error],
        )
        mock_ipython = mocker.patch("kedro.extras.extensions.ipython.get_ipython")

        load_ipython_extension(mocker.MagicMock())

        assert not mock_ipython().called
        assert not mock_ipython().push.called

        log_messages = [
            record.getMessage()
            for record in caplog.records
            if record.levelname == "ERROR"
        ]
        assert log_messages == [expected_log_message]
