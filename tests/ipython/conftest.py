import inspect

import pytest
from IPython.testing.globalipapp import get_ipython

from kedro.framework.startup import ProjectMetadata
from kedro.ipython import (
    load_ipython_extension,
)
from kedro.pipeline import node
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline

from . import dummy_function_fixtures  # noqa It is needed for the inspect module
from .dummy_function_fixtures import (
    dummy_function,
    dummy_function_with_loop,
    dummy_function_with_variable_length,
    dummy_nested_function,
)

# Constants
PACKAGE_NAME = "fake_package_name"
PROJECT_NAME = "fake_project_name"
PROJECT_INIT_VERSION = "0.1"


# Fixture
@pytest.fixture(autouse=True)
def cleanup_pipeline():
    yield
    from kedro.framework.project import pipelines

    pipelines.configure()


@pytest.fixture(scope="module", autouse=True)  # get_ipython() twice will result in None
def ipython():
    ipython = get_ipython()
    load_ipython_extension(ipython)
    return ipython


@pytest.fixture(autouse=True)
def fake_metadata(tmp_path):
    metadata = ProjectMetadata(
        source_dir=tmp_path / "src",  # default
        config_file=tmp_path / "pyproject.toml",
        package_name=PACKAGE_NAME,
        project_name=PROJECT_NAME,
        kedro_init_version=PROJECT_INIT_VERSION,
        project_path=tmp_path,
        tools=None,
        example_pipeline=None,
    )
    return metadata


@pytest.fixture(autouse=True)
def mock_kedro_project(mocker, fake_metadata):
    mocker.patch("kedro.ipython.bootstrap_project", return_value=fake_metadata)
    mocker.patch("kedro.ipython.configure_project")
    mocker.patch("kedro.ipython.KedroSession.create")


@pytest.fixture
def dummy_pipelines(dummy_node):
    # return a dict of pipelines
    return {"dummy_pipeline": modular_pipeline([dummy_node])}


def _get_function_definition_literal(func):
    source_lines, _ = inspect.getsourcelines(func)
    return "".join(source_lines)


@pytest.fixture
def dummy_function_defintion():
    return _get_function_definition_literal(dummy_function)


@pytest.fixture
def dummy_nested_function_literal():
    return _get_function_definition_literal(dummy_nested_function)


@pytest.fixture
def dummy_function_with_loop_literal():
    return _get_function_definition_literal(dummy_function_with_loop)


@pytest.fixture
def dummy_module_literal():
    # string representation of a dummy function includes imports, comments, and a
    # file function
    file_lines = inspect.getsource(dummy_function_fixtures)
    return file_lines


@pytest.fixture
def dummy_node():
    return node(
        func=dummy_function,
        inputs=["dummy_input", "extra_input"],
        outputs=["dummy_output"],
        name="dummy_node",
    )


@pytest.fixture
def dummy_node_empty_input():
    return node(
        func=dummy_function,
        inputs=["", ""],
        outputs=None,
        name="dummy_node_empty_input",
    )


@pytest.fixture
def dummy_node_dict_input():
    return node(
        func=dummy_function,
        inputs=dict(dummy_input="dummy_input", my_input="extra_input"),
        outputs=["dummy_output"],
        name="dummy_node_empty_input",
    )


@pytest.fixture
def dummy_node_with_variable_length():
    return node(
        func=dummy_function_with_variable_length,
        inputs=["dummy_input", "extra_input", "first", "second"],
        outputs=["dummy_output"],
        name="dummy_node_with_variable_length",
    )


@pytest.fixture
def lambda_node():
    return node(
        func=lambda x: x,
        inputs=[
            "x",
        ],
        outputs=["lambda_output"],
        name="lambda_node",
    )
