import logging
import re

import pytest
from dynaconf.validator import Validator

from kedro.framework.hooks import hook_impl
from kedro.framework.project import _ProjectSettings, pipelines
from kedro.framework.session import KedroSession
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
        assert pipelines == expected_pipelines


class TestDuplicatePipelineRegistration:
    """Test to make sure that if pipelines are defined in both registration hooks
    and pipelines_registry, they are deduplicated and a warning is displayed.
    """

    @pytest.mark.usefixtures("mock_settings_duplicate_hooks")
    def test_register_pipelines_with_duplicate_entries(
        self, tmp_path, mock_package_name, mock_pipeline
    ):
        KedroSession.create(mock_package_name, tmp_path)
        # check that all pipeline dictionaries merged together correctly
        expected_pipelines = {key: mock_pipeline for key in ("__default__", "pipe")}
        pattern = (
            "Found duplicate pipeline entries. The following "
            "will be overwritten: __default__"
        )
        with pytest.warns(UserWarning, match=re.escape(pattern)):
            assert pipelines == expected_pipelines
