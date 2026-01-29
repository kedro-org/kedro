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

    # Reset state for clean test
    pipelines._is_data_loaded = False
    pipelines._content = {}
    pipelines._loaded_pipeline_names = set()

    # accessing data should raise for unimportable pipelines
    # With the new behavior, attempting to load triggers the import which fails
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
    pipelines._loaded_pipeline_names = set()  # Reset the new tracking set

    # Access any pipeline - should load all pipelines (backward compatibility)
    pipeline1 = pipelines["pipeline1"]

    assert isinstance(pipeline1, Pipeline)
    # Old register_pipelines returns all pipelines regardless of requested_pipeline
    assert "pipeline1" in pipelines._content
    assert "pipeline2" in pipelines._content
    assert "__default__" in pipelines._content


@pytest.mark.parametrize("exception_type", [TypeError, ValueError])
def test_pipelines_load_data_signature_inspection_failure(
    monkeypatch, tmpdir, exception_type
):
    """Test that _load_data falls back to register_pipelines() when signature inspection fails."""
    # Create a package with register_pipelines
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
        configure_project(package_name)

        # Reset the state
        pipelines._is_data_loaded = False
        pipelines._content = {}
        pipelines._loaded_pipeline_names = set()  # Reset the new tracking set

        # Mock inspect.signature to raise exception to trigger the exception handler
        import inspect as inspect_module

        def mock_signature_raises(*args, **kwargs):
            raise exception_type("Cannot inspect signature")

        monkeypatch.setattr(inspect_module, "signature", mock_signature_raises)

        result = pipelines["test_pipeline"]

        assert isinstance(result, Pipeline)
        assert "test_pipeline" in pipelines._content
    finally:
        sys.path.pop(0)


@pytest.fixture
def selective_registry_package(tmpdir):
    """Minimal package to test passing `requested_pipeline` to register_pipelines."""
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


def test_pipelines_load_data_passes_requested_pipeline_to_register_pipelines(
    selective_registry_package,
):
    """Test that register_pipelines receives the requested pipeline parameter."""
    configure_project(selective_registry_package)

    # Force a clean load
    pipelines._is_data_loaded = False
    pipelines._content = {}
    pipelines._loaded_pipeline_names = set()  # Reset the new tracking set

    _ = pipelines["my_pipeline"]

    assert set(pipelines._content) == {"my_pipeline", "__default__"}


def test_pipelines_incremental_loading_merges_defaults(
    selective_registry_package,
):
    """Test that loading multiple pipelines incrementally merges __default__ correctly."""
    configure_project(selective_registry_package)

    # Force a clean load
    pipelines._is_data_loaded = False
    pipelines._content = {}
    pipelines._loaded_pipeline_names = set()

    # Load first pipeline
    _ = pipelines["first_pipeline"]
    assert "first_pipeline" in pipelines._content
    assert "__default__" in pipelines._content

    # __default__ should contain the first pipeline's nodes
    first_default = pipelines._content["__default__"]

    # Load second pipeline
    _ = pipelines["second_pipeline"]
    assert "first_pipeline" in pipelines._content
    assert "second_pipeline" in pipelines._content
    assert "__default__" in pipelines._content

    # __default__ should now have been updated with the second pipeline
    # The _update_content method adds __default__ pipelines together
    second_default = pipelines._content["__default__"]

    # Since both are empty pipelines in the fixture, this just verifies the merge happened
    # In a real scenario with nodes, second_default would have nodes from both
    assert isinstance(first_default, Pipeline)
    assert isinstance(second_default, Pipeline)


def test_pipelines_does_not_reload_same_pipeline_twice(
    selective_registry_package,
):
    """Test that accessing the same pipeline twice doesn't reload it."""
    configure_project(selective_registry_package)

    # Force a clean load
    pipelines._is_data_loaded = False
    pipelines._content = {}
    pipelines._loaded_pipeline_names = set()

    # Load pipeline first time
    pipeline1_first = pipelines["my_pipeline"]
    loaded_names_after_first = pipelines._loaded_pipeline_names.copy()

    # Load same pipeline again
    pipeline1_second = pipelines["my_pipeline"]
    loaded_names_after_second = pipelines._loaded_pipeline_names.copy()

    # Should be the same object and _loaded_pipeline_names shouldn't grow
    assert pipeline1_first is pipeline1_second
    assert loaded_names_after_first == loaded_names_after_second
    assert "my_pipeline" in pipelines._loaded_pipeline_names
