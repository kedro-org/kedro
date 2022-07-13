import sys
import textwrap

import pytest

from kedro.framework.project import find_pipelines


@pytest.fixture
def mock_package_with_pipelines(tmp_path, request):
    pipelines_dir = tmp_path / "test_package" / "pipelines"
    pipelines_dir.mkdir(parents=True)
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
    yield
    sys.path.pop(0)


@pytest.fixture
def pipeline_names(request):
    return request.param


@pytest.mark.parametrize(
    "mock_package_with_pipelines,pipeline_names",
    [(x, x) for x in [set()]],
    indirect=True,
)
def test_pipelines_without_configure_project_is_empty(
    mock_package_with_pipelines,  # pylint: disable=unused-argument
    pipeline_names,
):
    pipelines = find_pipelines()
    assert set(pipelines) == pipeline_names | {"__default__"}
    assert sum(pipelines.values()).outputs() == pipeline_names
