import sys
import textwrap

import pytest

from kedro.framework.project import configure_project, pipelines
from kedro.pipeline import Pipeline


@pytest.fixture
def mock_package_name_with_pipelines_file(tmpdir):
    pipelines_file_path = tmpdir.mkdir("test_package") / "pipeline_registry.py"
    pipelines_file_path.write(
        textwrap.dedent(
            """
                from kedro.pipeline import Pipeline
                def register_pipelines():
                    return {"new_pipeline": Pipeline([])}
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition("test_package")
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_pipelines_without_configure_project_is_empty(
    mock_package_name_with_pipelines_file,
):
    # Reimport `pipelines` from `kedro.framework.project` to ensure that
    # it was not set by a prior call to the `configure_project` function.
    del sys.modules["kedro.framework.project"]
    from kedro.framework.project import pipelines

    assert pipelines == {}


@pytest.fixture
def mock_package_name_with_unimportable_pipelines_file(tmpdir):
    pipelines_file_path = tmpdir.mkdir("test_broken_package") / "pipeline_registry.py"
    pipelines_file_path.write(
        textwrap.dedent(
            """
                import this_is_not_a_real_thing
                from kedro.pipeline import Pipeline
                def register_pipelines():
                    return {"new_pipeline": Pipeline([])}
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition(
        "test_broken_package"
    )
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_pipelines_after_configuring_project_shows_updated_values(
    mock_package_name_with_pipelines_file,
):
    configure_project(mock_package_name_with_pipelines_file)
    assert isinstance(pipelines["new_pipeline"], Pipeline)


def test_configure_project_should_not_raise_for_unimportable_pipelines(
    mock_package_name_with_unimportable_pipelines_file,
):
    # configure_project should not raise error for unimportable pipelines
    # since pipelines loading is lazy
    configure_project(mock_package_name_with_unimportable_pipelines_file)

    # accessing data should raise for unimportable pipelines
    with pytest.raises(
        ModuleNotFoundError, match="No module named 'this_is_not_a_real_thing'"
    ):
        _ = pipelines["new_pipeline"]


@pytest.fixture
def mock_package_name_with_selective_pipelines_file(tmpdir):
    """Fixture for a package with register_pipelines that accepts pipeline parameter."""
    pipelines_file_path = (
        tmpdir.mkdir("test_selective_package") / "pipeline_registry.py"
    )
    pipelines_file_path.write(
        textwrap.dedent(
            """
            from kedro.framework.project import find_pipelines
            from kedro.pipeline import Pipeline

            def register_pipelines(pipeline: str | None = None):
                pipelines = find_pipelines(raise_errors=True, name=pipeline)
                pipelines["__default__"] = sum(pipelines.values())
                return pipelines
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition(
        "test_selective_package"
    )
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


@pytest.fixture
def mock_package_name_with_old_pipelines_file(tmpdir):
    """Fixture for a package with register_pipelines that does NOT accept pipeline parameter."""
    pipelines_file_path = tmpdir.mkdir("test_old_package") / "pipeline_registry.py"
    pipelines_file_path.write(
        textwrap.dedent(
            """
            from kedro.pipeline import Pipeline

            def register_pipelines():
                return {
                    "pipeline1": Pipeline([]),
                    "pipeline2": Pipeline([]),
                    "__default__": Pipeline([]),
                }
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition(
        "test_old_package"
    )
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_pipelines_load_data_backward_compatibility(
    mock_package_name_with_old_pipelines_file,
):
    """Test that _load_data works with old register_pipelines that doesn't accept pipeline parameter."""
    configure_project(mock_package_name_with_old_pipelines_file)

    # Reset the state to ensure fresh load
    pipelines._is_data_loaded = False
    pipelines._content = {}

    # Access any pipeline - should load all pipelines (backward compatibility)
    pipeline1 = pipelines["pipeline1"]

    assert isinstance(pipeline1, Pipeline)
    # Old register_pipelines returns all pipelines regardless of requested_pipeline
    assert "pipeline1" in pipelines._content
    assert "pipeline2" in pipelines._content
    assert "__default__" in pipelines._content
