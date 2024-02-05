import pytest
from IPython.testing.globalipapp import get_ipython

from kedro.framework.startup import ProjectMetadata
from kedro.ipython import (
    load_ipython_extension,
)
from kedro.pipeline import node

# Constants
PACKAGE_NAME = "fake_package_name"
PROJECT_NAME = "fake_project_name"
PROJECT_INIT_VERSION = "0.1"


# Dummy functions
def dummy_function(dummy_input, my_input):
    """
    Returns True if input is not
    """
    # this is an in-line comment in the body of the function
    random_assignment = "Added for a longer function"
    random_assignment += "make sure to modify variable"
    return not dummy_input


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
def dummy_function_defintion():
    body = '''def dummy_function(dummy_input, my_input):
    """
    Returns True if input is not
    """
    # this is an in-line comment in the body of the function
    random_assignment = "Added for a longer function"
    random_assignment += "make sure to modify variable"
    return not dummy_input
'''
    return body


@pytest.fixture
def dummy_node():
    return node(
        func=dummy_function,
        inputs=["dummy_input", "extra_input"],
        outputs=["dummy_output"],
        name="dummy_node",
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
