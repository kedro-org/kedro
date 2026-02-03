import sys
import textwrap

import pytest

from kedro.framework import project
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


@pytest.fixture
def mock_package_name_with_selective_pipelines_file(tmpdir):
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


@pytest.fixture
def selective_registry_package(tmpdir):
    pipelines_file = tmpdir.mkdir("test_selective_registry") / "pipeline_registry.py"
    pipelines_file.write(
        textwrap.dedent(
            """
            from kedro.pipeline import Pipeline

            def register_pipelines(pipeline=None):
                if pipeline is None:
                    return {"__default__": Pipeline([])}
                return {
                    pipeline: Pipeline([]),
                    "__default__": Pipeline([]),
                }
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file).rpartition(
        "test_selective_registry"
    )
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_pipelines_without_configure_project_is_empty():
    # Create a fresh project module reference
    import kedro.framework.project as fresh_project

    # Reset to unconfigured state
    fresh_project.PACKAGE_NAME = None
    fresh_project.pipelines.configure(None)

    assert fresh_project.pipelines == {}


def test_pipelines_after_configuring_project_shows_updated_values(
    mock_package_name_with_pipelines_file,
):
    project.configure_project(mock_package_name_with_pipelines_file)
    assert isinstance(project.pipelines["new_pipeline"], Pipeline)


def test_configure_project_should_not_raise_for_unimportable_pipelines(
    mock_package_name_with_unimportable_pipelines_file,
):
    project.configure_project(mock_package_name_with_unimportable_pipelines_file)

    with pytest.raises(
        ModuleNotFoundError, match="No module named 'this_is_not_a_real_thing'"
    ):
        _ = project.pipelines["new_pipeline"]


@pytest.mark.parametrize("exception_type", [TypeError, ValueError])
def test_pipelines_load_data_signature_inspection_failure(
    monkeypatch, tmpdir, exception_type
):
    pipelines_file_path = (
        tmpdir.mkdir(f"test_sig_fail_{exception_type.__name__}")
        / "pipeline_registry.py"
    )
    pipelines_file_path.write(
        textwrap.dedent(
            """
            from kedro.pipeline import Pipeline
            def register_pipelines():
                return {"test_pipeline": Pipeline([])}
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition(
        f"test_sig_fail_{exception_type.__name__}"
    )
    sys.path.insert(0, project_path)

    try:
        project.configure_project(package_name)

        import inspect as inspect_module

        def mock_signature_raises(*args, **kwargs):
            raise exception_type("Cannot inspect signature")

        monkeypatch.setattr(inspect_module, "signature", mock_signature_raises)

        result = project.pipelines["test_pipeline"]

        assert isinstance(result, Pipeline)
        assert "test_pipeline" in project.pipelines._content
    finally:
        sys.path.pop(0)
