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
import logging
import re
from typing import Any, Dict, Iterable, Optional

import pytest
from dynaconf.validator import Validator

from kedro.config import ConfigLoader
from kedro.framework.context import KedroContextError
from kedro.framework.hooks import hook_impl
from kedro.framework.project import _ProjectSettings, settings
from kedro.framework.session import KedroSession
from kedro.io import DataCatalog
from kedro.versioning import Journal
from tests.framework.session.conftest import (
    _assert_hook_call_record_has_expected_parameters,
    _mock_imported_settings_paths,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def pipeline_registration_hook(mock_pipeline):
    class PipelineHook:
        @hook_impl
        def register_pipelines(self):
            logger.info("Registering pipelines")
            return {"__default__": mock_pipeline}

    return PipelineHook()


def _mock_settings_with_hooks(mocker, hooks):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=hooks)

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_settings_with_pipeline_hooks(
    mocker, project_hooks, pipeline_registration_hook
):
    return _mock_settings_with_hooks(
        mocker, hooks=(project_hooks, pipeline_registration_hook)
    )


@pytest.fixture
def mock_settings_duplicate_hooks(mocker, project_hooks, pipeline_registration_hook):
    return _mock_settings_with_hooks(
        mocker,
        hooks=(project_hooks, pipeline_registration_hook, pipeline_registration_hook),
    )


class RequiredRegistrationHooks:
    """Mandatory registration hooks"""

    @hook_impl
    def register_config_loader(self, conf_paths: Iterable[str]) -> ConfigLoader:
        return ConfigLoader(conf_paths)

    @hook_impl
    def register_catalog(
        self,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]],
        load_versions: Dict[str, str],
        save_version: str,
        journal: Journal,
    ) -> DataCatalog:
        return DataCatalog.from_config(  # pragma: no cover
            catalog, credentials, load_versions, save_version, journal
        )


@pytest.fixture
def mock_settings_broken_config_loader_hooks(mocker):
    class BrokenConfigLoaderHooks(RequiredRegistrationHooks):
        @hook_impl
        def register_config_loader(self):  # pylint: disable=arguments-differ
            return None

    return _mock_settings_with_hooks(mocker, hooks=(BrokenConfigLoaderHooks(),))


@pytest.fixture
def mock_settings_broken_catalog_hooks(mocker):
    class BrokenCatalogHooks(RequiredRegistrationHooks):
        @hook_impl
        def register_catalog(self):  # pylint: disable=arguments-differ
            return None

    return _mock_settings_with_hooks(mocker, hooks=(BrokenCatalogHooks(),))


@pytest.fixture
def mock_session(
    mock_settings_with_pipeline_hooks, mock_package_name, tmp_path
):  # pylint: disable=unused-argument
    return KedroSession.create(
        mock_package_name, tmp_path, extra_params={"params:key": "value"}
    )


class TestRegistrationHooks:
    def test_register_pipelines_is_called(
        self, dummy_dataframe, caplog, mock_session, mock_pipeline
    ):
        context = mock_session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)
        mock_session.run()

        register_pipelines_calls = [
            record
            for record in caplog.records
            if record.funcName == "register_pipelines"
        ]
        assert len(register_pipelines_calls) == 1
        call_record = register_pipelines_calls[0]
        assert call_record.getMessage() == "Registering pipelines"
        _assert_hook_call_record_has_expected_parameters(call_record, [])

        expected_pipelines = {
            "__default__": mock_pipeline,
            "pipe": mock_pipeline,
        }
        assert context.pipelines == expected_pipelines

    def test_register_config_loader_is_called(self, mock_session, caplog):
        context = mock_session.load_context()
        _ = context.config_loader

        relevant_records = [
            r for r in caplog.records if r.getMessage() == "Registering config loader"
        ]
        assert len(relevant_records) == 1

        record = relevant_records[0]
        expected_conf_paths = [
            str(context.project_path / settings.CONF_ROOT / "base"),
            str(context.project_path / settings.CONF_ROOT / "local"),
        ]
        assert record.conf_paths == expected_conf_paths
        assert record.env == context.env
        assert record.extra_params == {"params:key": "value"}

    def test_register_catalog_is_called(self, mock_session, caplog):
        context = mock_session.load_context()
        catalog = context.catalog
        assert isinstance(catalog, DataCatalog)

        relevant_records = [
            r for r in caplog.records if r.getMessage() == "Registering catalog"
        ]
        assert len(relevant_records) == 1

        record = relevant_records[0]
        assert record.catalog.keys() == {"cars", "boats"}
        assert record.credentials == {"dev_s3": "foo"}
        # save_version is only passed during a run, not on the property getter
        assert record.save_version is None
        assert record.load_versions is None
        assert record.journal is None


class TestDuplicatePipelineRegistration:
    """Test to make sure that if pipelines are defined in both registration hooks
    and pipelines_registry, they are deduplicated and a warning is displayed.
    """

    @pytest.mark.usefixtures("mock_settings_duplicate_hooks")
    def test_register_pipelines_with_duplicate_entries(
        self, tmp_path, mock_package_name, mock_pipeline
    ):
        session = KedroSession.create(mock_package_name, tmp_path)
        context = session.load_context()
        # check that all pipeline dictionaries merged together correctly
        expected_pipelines = {key: mock_pipeline for key in ("__default__", "pipe")}
        pattern = (
            "Found duplicate pipeline entries. The following "
            "will be overwritten: __default__"
        )
        with pytest.warns(UserWarning, match=re.escape(pattern)):
            assert context.pipelines == expected_pipelines


class TestBrokenRegistrationHooks:
    @pytest.mark.usefixtures("mock_settings_broken_config_loader_hooks")
    def test_broken_register_config_loader_hook(self, tmp_path, mock_package_name):
        pattern = "Expected an instance of `ConfigLoader`, got `NoneType` instead."
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            KedroSession.create(mock_package_name, tmp_path)

    @pytest.mark.usefixtures("mock_settings_broken_catalog_hooks")
    def test_broken_register_catalog_hook(self, tmp_path, mock_package_name):
        pattern = "Expected an instance of `DataCatalog`, got `NoneType` instead."
        with KedroSession.create(mock_package_name, tmp_path) as session:
            context = session.load_context()
            with pytest.raises(KedroContextError, match=re.escape(pattern)):
                _ = context.catalog
