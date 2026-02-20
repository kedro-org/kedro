import shutil
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

from kedro.framework.project import configure_project, find_pipelines


@pytest.fixture
def mock_package_name_with_pipelines(tmp_path, request):
    package_name = "test_package"
    pipelines_dir = tmp_path / package_name / "pipelines"
    pipelines_dir.mkdir(parents=True)
    (pipelines_dir / "__init__.py").touch()
    for pipeline_name in request.param:
        pipeline_dir = pipelines_dir / pipeline_name
        pipeline_dir.mkdir()
        (pipeline_dir / "__init__.py").write_text(
            textwrap.dedent(
                f"""
                from kedro.pipeline import Pipeline, node, pipeline


                def create_pipeline(**kwargs) -> Pipeline:
                    return pipeline([node(lambda: 1, None, "{pipeline_name}")])
                """
            )
        )
    sys.path.insert(0, str(tmp_path))
    yield package_name
    sys.path.pop(0)

    # Make sure that any new `test_package.pipeline` module gets loaded.
    if f"{package_name}.pipeline" in sys.modules:
        del sys.modules[f"{package_name}.pipeline"]

    # Make sure that the `importlib.resources.files` in `find_pipelines`
    # will point to the correct `test_package.pipelines` not from cache.
    if f"{package_name}.pipelines" in sys.modules:
        del sys.modules[f"{package_name}.pipelines"]


@pytest.fixture
def pipeline_names(request):
    return request.param


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names",
    [(x, x) for x in [set(), {"my_pipeline"}]],
    indirect=True,
)
def test_find_pipelines(mock_package_name_with_pipelines, pipeline_names):
    configure_project(mock_package_name_with_pipelines)
    pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names",
    [(x, x) for x in [set(), {"good_pipeline"}]],
    indirect=True,
)
def test_find_pipelines_skips_modules_without_create_pipelines_function(
    mock_package_name_with_pipelines, pipeline_names
):
    # Create a module without `create_pipelines` in the `pipelines` dir.
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    pipeline_dir = pipelines_dir / "bad_touch"
    pipeline_dir.mkdir()
    (pipeline_dir / "__init__.py").touch()

    configure_project(mock_package_name_with_pipelines)
    with pytest.warns(
        UserWarning, match="module does not expose a 'create_pipeline' function"
    ):
        pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names",
    [(x, x) for x in [set(), {"my_pipeline"}]],
    indirect=True,
)
def test_find_pipelines_skips_hidden_modules(
    mock_package_name_with_pipelines, pipeline_names
):
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    pipeline_dir = pipelines_dir / ".ipynb_checkpoints"
    pipeline_dir.mkdir()
    (pipeline_dir / "__init__.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            from kedro.pipeline import Pipeline, node, pipeline


            def create_pipeline(**kwargs) -> Pipeline:
                return pipeline([node(lambda: 1, None, "simple_pipeline")])
            """
        )
    )

    configure_project(mock_package_name_with_pipelines)
    pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names",
    [(x, x) for x in [set(), {"my_pipeline"}]],
    indirect=True,
)
def test_find_pipelines_skips_modules_with_unexpected_return_value_type(
    mock_package_name_with_pipelines, pipeline_names
):
    # Define `create_pipelines` so that it does not return a `Pipeline`.
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    pipeline_dir = pipelines_dir / "not_my_pipeline"
    pipeline_dir.mkdir()
    (pipeline_dir / "__init__.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            from kedro.pipeline import Pipeline, node, pipeline


            def create_pipeline(**kwargs) -> dict[str, Pipeline]:
                return {
                    "pipe1": pipeline([node(lambda: 1, None, "pipe1")]),
                    "pipe2": pipeline([node(lambda: 2, None, "pipe2")]),
                }
            """
        )
    )

    configure_project(mock_package_name_with_pipelines)
    with pytest.warns(
        UserWarning,
        match=(
            r"Expected the 'create_pipeline' function in the '\S+' "
            r"module to return a 'Pipeline' object, got 'dict' instead."
        ),
    ):
        pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names",
    [(x, x) for x in [set(), {"my_pipeline"}]],
    indirect=True,
)
def test_find_pipelines_skips_regular_files_within_the_pipelines_folder(
    mock_package_name_with_pipelines, pipeline_names
):
    # Create a regular file (not a subdirectory) in the `pipelines` dir.
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    (pipelines_dir / "not_my_pipeline.py").touch()

    configure_project(mock_package_name_with_pipelines)
    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=UserWarning)
        pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names,raise_errors",
    [
        (x, x, raise_errors)
        for x in [set(), {"my_pipeline"}]
        for raise_errors in [True, False]
    ],
    indirect=["mock_package_name_with_pipelines", "pipeline_names"],
)
def test_find_pipelines_skips_modules_that_cause_exceptions_upon_import(
    mock_package_name_with_pipelines, pipeline_names, raise_errors
):
    # Create a module that will result in errors when we try to load it.
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    pipeline_dir = pipelines_dir / "boulevard_of_broken_pipelines"
    pipeline_dir.mkdir()
    (pipeline_dir / "__init__.py").write_text("I walk a lonely road...")

    configure_project(mock_package_name_with_pipelines)
    with getattr(pytest, "raises" if raise_errors else "warns")(
        ImportError if raise_errors else UserWarning,
        match=r"An error occurred while importing the '\S+' module.",
    ):
        pipelines = find_pipelines(raise_errors=raise_errors)
    if not raise_errors:
        assert set(pipelines) == pipeline_names | {"__default__"}
        assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names",
    [(x, x) for x in [set(), {"my_pipeline"}]],
    indirect=True,
)
def test_find_pipelines_handles_simplified_project_structure(
    mock_package_name_with_pipelines, pipeline_names
):
    (Path(sys.path[0]) / mock_package_name_with_pipelines / "pipeline.py").write_text(
        textwrap.dedent(
            """
            from kedro.pipeline import Pipeline, node, pipeline


            def create_pipeline(**kwargs) -> Pipeline:
                return pipeline([node(lambda: 1, None, "simple_pipeline")])
            """
        )
    )

    configure_project(mock_package_name_with_pipelines)
    pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names | {"simple_pipeline"}


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,pipeline_names,raise_errors",
    [
        (x, x, raise_errors)
        for x in [set(), {"my_pipeline"}]
        for raise_errors in [True, False]
    ],
    indirect=["mock_package_name_with_pipelines", "pipeline_names"],
)
def test_find_pipelines_skips_unimportable_pipeline_module(
    mock_package_name_with_pipelines, pipeline_names, raise_errors
):
    (Path(sys.path[0]) / mock_package_name_with_pipelines / "pipeline.py").write_text(
        textwrap.dedent(
            f"""
            import {"".join(pipeline_names)}

            from kedro.pipeline import Pipeline, node, pipeline


            def create_pipeline(**kwargs) -> Pipeline:
                return pipeline([node(lambda: 1, None, "simple_pipeline")])
            """
        )
    )

    configure_project(mock_package_name_with_pipelines)
    with getattr(pytest, "raises" if raise_errors else "warns")(
        ImportError if raise_errors else UserWarning,
        match=r"An error occurred while importing the '\S+' module.",
    ):
        pipelines = find_pipelines(raise_errors=raise_errors)
    if not raise_errors:
        assert set(pipelines) == pipeline_names | {"__default__"}
        assert sum(pipelines.values()).outputs() == pipeline_names


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines,simplified",
    [(set(), False), (set(), True)],
    indirect=["mock_package_name_with_pipelines"],
)
def test_find_pipelines_handles_project_structure_without_pipelines_dir(
    mock_package_name_with_pipelines, simplified
):
    # Delete the `pipelines` directory to simulate a project without it.
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    shutil.rmtree(pipelines_dir)

    if simplified:
        (
            Path(sys.path[0]) / mock_package_name_with_pipelines / "pipeline.py"
        ).write_text(
            textwrap.dedent(
                """
                from kedro.pipeline import Pipeline, node, pipeline


                def create_pipeline(**kwargs) -> Pipeline:
                    return pipeline([node(lambda: 1, None, "simple_pipeline")])
                """
            )
        )

    configure_project(mock_package_name_with_pipelines)
    pipelines = find_pipelines()
    assert set(pipelines) == {"__default__"}
    assert sum(pipelines.values()).outputs() == (
        {"simple_pipeline"} if simplified else set()
    )


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2", "pipeline3"}],
    indirect=True,
)
def test_find_pipelines_with_name_loads_only_requested_pipeline(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name=...) only loads and returns the requested pipeline."""
    configure_project(mock_package_name_with_pipelines)

    pipelines = find_pipelines(name="pipeline2")

    # Should only return the requested pipeline, not all pipelines
    assert set(pipelines.keys()) == {"pipeline2"}
    assert sum(pipelines.values()).outputs() == {"pipeline2"}


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"my_pipeline"}],
    indirect=True,
)
def test_find_pipelines_with_name_raise_errors_true(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name=..., raise_errors=True) raises ImportError when pipeline doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    with pytest.raises(
        ImportError,
        match=r"An error occurred while importing the '.*pipelines\.does_not_exist' module.",
    ):
        find_pipelines(name="does_not_exist", raise_errors=True)


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"my_pipeline"}],
    indirect=True,
)
def test_find_pipelines_with_name_raise_errors_false(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name=..., raise_errors=False) issues warning when pipeline doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    with pytest.warns(
        UserWarning,
        match=r"An error occurred while importing the '.*pipelines\.does_not_exist' module.",
    ):
        pipelines = find_pipelines(name="does_not_exist", raise_errors=False)
        # Should return empty dict (the pipeline is not loaded)
        assert "does_not_exist" not in pipelines


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"my_pipeline"}],
    indirect=True,
)
def test_find_pipelines_with_name_warns_when_pipeline_has_no_create_function(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name=..., raise_errors=False) issues warning when
    pipeline module exists but has no create_pipeline function."""
    configure_project(mock_package_name_with_pipelines)

    # Create a pipeline module that doesn't have create_pipeline function
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    pipeline_dir = pipelines_dir / "empty_pipeline"
    pipeline_dir.mkdir()
    (pipeline_dir / "__init__.py").touch()  # Empty file, no create_pipeline function

    # With raise_errors=False, should warn but not raise
    with pytest.warns(
        UserWarning, match="module does not expose a 'create_pipeline' function"
    ):
        pipelines = find_pipelines(name="empty_pipeline", raise_errors=False)
        # The pipeline should not be in the results
        assert "empty_pipeline" not in pipelines


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"my_pipeline"}],
    indirect=True,
)
def test_find_pipelines_with_name_raises_keyerror_when_pipeline_has_no_create_function(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name=..., raise_errors=True) raises KeyError when
    pipeline module exists but has no create_pipeline function."""
    configure_project(mock_package_name_with_pipelines)

    # Create a pipeline module that doesn't have create_pipeline function
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    pipeline_dir = pipelines_dir / "empty_pipeline"
    pipeline_dir.mkdir()
    (pipeline_dir / "__init__.py").touch()  # Empty file, no create_pipeline function

    # With raise_errors=True, should raise KeyError
    with pytest.raises(KeyError, match="Pipeline 'empty_pipeline' not found"):
        find_pipelines(name="empty_pipeline", raise_errors=True)


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2"}],
    indirect=True,
)
def test_find_pipelines_with_default_name_loads_all_pipelines(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name='__default__') loads all pipelines, not selective."""
    configure_project(mock_package_name_with_pipelines)

    pipelines = find_pipelines(name="__default__")

    # Should load all pipelines, not just one
    assert "__default__" in pipelines
    assert "pipeline1" in pipelines
    assert "pipeline2" in pipelines


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2", "pipeline3"}],
    indirect=True,
)
def test_find_pipelines_with_multiple_names_loads_only_requested_pipelines(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name='p1,p2') loads only the requested pipelines."""
    configure_project(mock_package_name_with_pipelines)

    pipelines = find_pipelines(name="pipeline1,pipeline3")

    # Should only return the requested pipelines, not all pipelines
    assert set(pipelines.keys()) == {"pipeline1", "pipeline3"}
    assert "pipeline2" not in pipelines
    assert "__default__" not in pipelines
    assert sum(pipelines.values()).outputs() == {"pipeline1", "pipeline3"}


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2", "pipeline3"}],
    indirect=True,
)
def test_find_pipelines_with_multiple_names_no_default(
    mock_package_name_with_pipelines,
):
    """Test that __default__ is not included when specific pipelines are requested."""
    configure_project(mock_package_name_with_pipelines)

    pipelines = find_pipelines(name="pipeline1,pipeline2")

    # __default__ should NOT be in the result
    assert "__default__" not in pipelines
    assert set(pipelines.keys()) == {"pipeline1", "pipeline2"}


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2"}],
    indirect=True,
)
def test_find_pipelines_with_multiple_names_one_missing_raise_errors_true(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines raises ImportError when one of multiple requested pipelines doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    with pytest.raises(
        ImportError,
        match=r"An error occurred while importing the '.*pipelines\.does_not_exist' module.",
    ):
        find_pipelines(name="pipeline1,does_not_exist", raise_errors=True)


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2"}],
    indirect=True,
)
def test_find_pipelines_with_multiple_names_one_missing_raise_errors_false(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines issues warning and returns valid pipelines when one doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    with pytest.warns(
        UserWarning,
        match=r"An error occurred while importing the '.*pipelines\.does_not_exist' module.",
    ):
        pipelines = find_pipelines(name="pipeline1,does_not_exist", raise_errors=False)

    # Should still return the valid pipeline
    assert "pipeline1" in pipelines
    assert "does_not_exist" not in pipelines
    assert "__default__" not in pipelines


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2", "pipeline3"}],
    indirect=True,
)
def test_find_pipelines_with_whitespace_in_names(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines handles whitespace in pipeline names correctly."""
    configure_project(mock_package_name_with_pipelines)

    # Test with various whitespace patterns
    pipelines = find_pipelines(name="pipeline1, pipeline2 , pipeline3")

    assert set(pipelines.keys()) == {"pipeline1", "pipeline2", "pipeline3"}
    assert "__default__" not in pipelines


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [{"pipeline1", "pipeline2"}],
    indirect=True,
)
def test_find_pipelines_empty_string_loads_all(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines(name='') loads all pipelines (treats empty as None)."""
    configure_project(mock_package_name_with_pipelines)

    pipelines = find_pipelines(name="")

    # Empty string should be treated as None (load all)
    assert "__default__" in pipelines
    assert "pipeline1" in pipelines
    assert "pipeline2" in pipelines


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [set()],  # Start with empty set (no pipelines)
    indirect=True,
)
def test_find_pipelines_when_pipelines_dir_missing_raise_errors_true(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines raises KeyError when specific pipeline requested but pipelines dir doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    # Delete the pipelines directory to simulate a project without it
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    shutil.rmtree(pipelines_dir)

    # Request a specific pipeline when no pipelines directory exists
    with pytest.raises(KeyError, match=r"Pipeline\(s\) not found: my_pipeline"):
        find_pipelines(name="my_pipeline", raise_errors=True)


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [set()],  # Start with empty set (no pipelines)
    indirect=True,
)
def test_find_pipelines_when_pipelines_dir_missing_raise_errors_false(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines warns when specific pipeline requested but pipelines dir doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    # Delete the pipelines directory to simulate a project without it
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    shutil.rmtree(pipelines_dir)

    # Request a specific pipeline when no pipelines directory exists
    with pytest.warns(UserWarning, match=r"Pipeline\(s\) not found: my_pipeline"):
        pipelines = find_pipelines(name="my_pipeline", raise_errors=False)
        # Should return empty dict (no pipelines loaded)
        assert pipelines == {}


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [set()],  # Start with empty set (no pipelines)
    indirect=True,
)
def test_find_multiple_pipelines_when_pipelines_dir_missing_raise_errors_true(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines raises KeyError when multiple pipelines requested but pipelines dir doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    # Delete the pipelines directory to simulate a project without it
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    shutil.rmtree(pipelines_dir)

    # Request multiple pipelines when no pipelines directory exists
    with pytest.raises(
        KeyError, match=r"Pipeline\(s\) not found: pipeline1, pipeline2"
    ):
        find_pipelines(name="pipeline1,pipeline2", raise_errors=True)


@pytest.mark.parametrize(
    "mock_package_name_with_pipelines",
    [set()],  # Start with empty set (no pipelines)
    indirect=True,
)
def test_find_multiple_pipelines_when_pipelines_dir_missing_raise_errors_false(
    mock_package_name_with_pipelines,
):
    """Test that find_pipelines warns when multiple pipelines requested but pipelines dir doesn't exist."""
    configure_project(mock_package_name_with_pipelines)

    # Delete the pipelines directory to simulate a project without it
    pipelines_dir = Path(sys.path[0]) / mock_package_name_with_pipelines / "pipelines"
    shutil.rmtree(pipelines_dir)

    # Request multiple pipelines when no pipelines directory exists
    with pytest.warns(
        UserWarning, match=r"Pipeline\(s\) not found: pipeline1, pipeline2"
    ):
        pipelines = find_pipelines(name="pipeline1,pipeline2", raise_errors=False)
        # Should return empty dict (no pipelines loaded)
        assert pipelines == {}
