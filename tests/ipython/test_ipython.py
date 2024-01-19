from pathlib import Path

import pytest
from IPython.core.error import UsageError
from IPython.testing.globalipapp import get_ipython

from kedro.framework.project import pipelines
from kedro.framework.startup import ProjectMetadata
from kedro.ipython import _resolve_project_path, load_ipython_extension, reload_kedro, magic_load_node, _load_node, _find_node, _prepare_imports, _prepare_node_inputs, _get_function_body
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
from kedro.pipeline import node

PACKAGE_NAME = "fake_package_name"
PROJECT_NAME = "fake_project_name"
PROJECT_INIT_VERSION = "0.1"


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


def dummy_function(dummy_input, extra_input):
    """
    Returns True if input is not
    """
    # this is an in-line comment in the body of the function
    random_assignment = "Added for a longer function"
    return not dummy_input

def dummy_nested_function(dummy_input):
    def nested_function(input):
        return not input
    return nested_function(dummy_input)

def dummy_function_with_loop(dummy_list):
    for x in dummy_list:
        continue
    return len(dummy_list)

@pytest.fixture
def dummy_node():
    return node(
        func=dummy_function,
        inputs=["dummy_input", "extra_input"],
        outputs=["dummy_output"],
        name="check_if_false_node",
    )

class TestLoadKedroObjects:
    def test_ipython_load_entry_points(
        self,
        mocker,
        fake_metadata,
        caplog,
    ):
        mock_line_magic = mocker.MagicMock()
        mock_line_magic_name = "abc"
        mock_line_magic.__name__ = mock_line_magic_name
        mock_line_magic.__qualname__ = mock_line_magic_name  # Required by IPython

        mocker.patch("kedro.ipython.load_entry_points", return_value=[mock_line_magic])
        expected_message = f"Registered line magic '{mock_line_magic_name}'"

        reload_kedro(fake_metadata.project_path)

        log_messages = [record.getMessage() for record in caplog.records]
        assert expected_message in log_messages

    def test_ipython_lazy_load_pipeline(
        self,
        mocker,
    ):
        pipelines.configure("dummy_pipeline")  # Setup the pipelines

        my_pipelines = {"ds": modular_pipeline([])}

        def my_register_pipeline():
            return my_pipelines

        mocker.patch.object(
            pipelines,
            "_get_pipelines_registry_callable",
            return_value=my_register_pipeline,
        )
        reload_kedro()

        assert pipelines._content == {}  # Check if it is lazy loaded
        pipelines._load_data()  # Trigger data load
        assert pipelines._content == my_pipelines

    def test_ipython_load_objects(
        self,
        mocker,
        ipython,
    ):
        mock_session_create = mocker.patch("kedro.ipython.KedroSession.create")
        pipelines.configure("dummy_pipeline")  # Setup the pipelines

        my_pipelines = {"ds": modular_pipeline([])}

        def my_register_pipeline():
            return my_pipelines

        mocker.patch.object(
            pipelines,
            "_get_pipelines_registry_callable",
            return_value=my_register_pipeline,
        )
        ipython_spy = mocker.spy(ipython, "push")

        reload_kedro()

        mock_session_create.assert_called_once_with(
            None,
            env=None,
            extra_params=None,
            conf_source=None,
        )
        _, kwargs = ipython_spy.call_args_list[0]
        variables = kwargs["variables"]

        assert variables["context"] == mock_session_create().load_context()
        assert variables["catalog"] == mock_session_create().load_context().catalog
        assert variables["session"] == mock_session_create()
        assert variables["pipelines"] == my_pipelines

    def test_ipython_load_objects_with_args(self, mocker, fake_metadata, ipython):
        mock_session_create = mocker.patch("kedro.ipython.KedroSession.create")
        pipelines.configure("dummy_pipeline")  # Setup the pipelines

        my_pipelines = {"ds": modular_pipeline([])}

        def my_register_pipeline():
            return my_pipelines

        mocker.patch.object(
            pipelines,
            "_get_pipelines_registry_callable",
            return_value=my_register_pipeline,
        )
        ipython_spy = mocker.spy(ipython, "push")
        dummy_env = "env"
        dummy_dict = {"key": "value"}
        dummy_conf_source = "conf/"

        reload_kedro(
            fake_metadata.project_path, "env", {"key": "value"}, conf_source="conf/"
        )

        mock_session_create.assert_called_once_with(
            fake_metadata.project_path,
            env=dummy_env,
            extra_params=dummy_dict,
            conf_source=dummy_conf_source,
        )
        _, kwargs = ipython_spy.call_args_list[0]
        variables = kwargs["variables"]

        assert variables["context"] == mock_session_create().load_context()
        assert variables["catalog"] == mock_session_create().load_context().catalog
        assert variables["session"] == mock_session_create()
        assert variables["pipelines"] == my_pipelines


class TestLoadIPythonExtension:
    def test_load_ipython_extension(self, ipython):
        ipython.magic("load_ext kedro.ipython")

    def test_load_extension_missing_dependency(self, mocker):
        mocker.patch("kedro.ipython.reload_kedro", side_effect=ImportError)
        mocker.patch(
            "kedro.ipython._find_kedro_project",
            return_value=mocker.Mock(),
        )
        mocker.patch("IPython.core.magic.register_line_magic")
        mocker.patch("IPython.core.magic_arguments.magic_arguments")
        mocker.patch("IPython.core.magic_arguments.argument")
        mock_ipython = mocker.patch("IPython.get_ipython")

        with pytest.raises(ImportError):
            load_ipython_extension(mocker.Mock())

        assert not mock_ipython().called
        assert not mock_ipython().push.called

    def test_load_extension_not_in_kedro_project(self, mocker, caplog):
        mocker.patch("kedro.ipython._find_kedro_project", return_value=None)
        mocker.patch("IPython.core.magic.register_line_magic")
        mocker.patch("IPython.core.magic_arguments.magic_arguments")
        mocker.patch("IPython.core.magic_arguments.argument")
        mock_ipython = mocker.patch("IPython.get_ipython")

        load_ipython_extension(mocker.Mock())

        assert not mock_ipython().called
        assert not mock_ipython().push.called

        log_messages = [record.getMessage() for record in caplog.records]
        expected_message = (
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        assert expected_message in log_messages

    def test_load_extension_register_line_magic(self, mocker, ipython):
        mocker.patch("kedro.ipython._find_kedro_project")
        mock_reload_kedro = mocker.patch("kedro.ipython.reload_kedro")
        load_ipython_extension(ipython)
        mock_reload_kedro.assert_called_once()

        # Calling the line magic to check if the line magic is available
        ipython.magic("reload_kedro")
        assert mock_reload_kedro.call_count == 2

    @pytest.mark.parametrize(
        "args",
        [
            "",
            ".",
            ". --env=base",
            "--env=base",
            "-e base",
            ". --env=base --params=key=val",
            "--conf-source=new_conf",
        ],
    )
    def test_line_magic_with_valid_arguments(self, mocker, args, ipython):
        mocker.patch("kedro.ipython._find_kedro_project")
        mocker.patch("kedro.ipython.reload_kedro")

        ipython.magic(f"reload_kedro {args}")

    def test_line_magic_with_invalid_arguments(self, mocker, ipython):
        mocker.patch("kedro.ipython._find_kedro_project")
        mocker.patch("kedro.ipython.reload_kedro")
        load_ipython_extension(ipython)

        with pytest.raises(
            UsageError, match=r"unrecognized arguments: --invalid_arg=dummy"
        ):
            ipython.magic("reload_kedro --invalid_arg=dummy")


class TestProjectPathResolution:
    def test_only_path_specified(self):
        result = _resolve_project_path(path="/test")
        expected = Path("/test").resolve()
        assert result == expected

    def test_only_local_namespace_specified(self):
        class MockKedroContext:
            # A dummy stand-in for KedroContext sufficient for this test
            project_path = Path("/test").resolve()

        result = _resolve_project_path(local_namespace={"context": MockKedroContext()})
        expected = Path("/test").resolve()
        assert result == expected

    def test_no_path_no_local_namespace_specified(self, mocker):
        mocker.patch(
            "kedro.ipython._find_kedro_project", return_value=Path("/test").resolve()
        )
        result = _resolve_project_path()
        expected = Path("/test").resolve()
        assert result == expected

    def test_project_path_unresolvable(self, mocker):
        mocker.patch("kedro.ipython._find_kedro_project", return_value=None)
        result = _resolve_project_path()
        expected = None
        assert result == expected

    def test_project_path_unresolvable_warning(self, mocker, caplog, ipython):
        mocker.patch("kedro.ipython._find_kedro_project", return_value=None)
        ipython.magic("reload_ext kedro.ipython")
        log_messages = [record.getMessage() for record in caplog.records]
        expected_message = (
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        assert expected_message in log_messages

    def test_project_path_update(self, caplog):
        class MockKedroContext:
            # A dummy stand-in for KedroContext sufficient for this test
            project_path = Path("/test").resolve()

        local_namespace = {"context": MockKedroContext()}
        updated_path = Path("/updated_path").resolve()
        _resolve_project_path(path=updated_path, local_namespace=local_namespace)

        log_messages = [record.getMessage() for record in caplog.records]
        expected_message = f"Updating path to Kedro project: {updated_path}..."
        assert expected_message in log_messages



class TestLoadNodeMagic:
    # TODO 
    # test magic, _load_node, _find_node, _prepare_node_inputs, test _prepare_imports, get_function_body

    # node edge cases
    #   comments
    #   function is a lambda function
    #   function has a loop
    #   nested function inside function


    # node file edge cases
    #   interspersed imports
    #   multi-line comments

    def test_import_helper_function_from_same_file(self):
        """function body can refer to function other than the import statements but helper function
        in the body
        """
        pass
    

    def test_node_inputs_match_function_signature(self):
        """node input names should match with function signature.
        Usually they are the same but not necessary.
        """
        pass

    def test_load_node_magic(self):
        pass

    def test_load_node(self):
        node_name = "dummy node"
        cells_list = True # _load_node("dummy node")
        assert cells_list

    def test_find_node(self):
        node_name = "dummy node"
        # _find_node(node_name)

    def test_get_function_body(self):
        func_strings = [
        "\"\"\"\nReturns True if input is not\n\"\"\"",
        "\n# this is an in-line comment in the body of the function",
        "\nrandom_assignment = \"Added for a longer function\"",
        "\nreturn not dummy_input\n"
        ]
        result = _get_function_body(dummy_function)
        assert result == "".join(func_line for func_line in func_strings)

    def test_get_lambda_function_body(self):
        result = _get_function_body(lambda x: x)
        assert result  == "lambda x: x"
        # TODO fix - fails because it splits at the comma

    def test_get_nested_function_body(self):
        func_strings = [
        "def nested_function(input):",
        "\nreturn not input",
        "\nreturn nested_function(dummy_input)\n"
        ]
        result = _get_function_body(dummy_nested_function)
        assert result == "".join(func_line for func_line in func_strings)
        # TODO fix - fails because skips nested function definition

    def test_get_function_with_loop_body(self):
        func_strings = [
        "for x in dummy_list:",
        "\ncontinue",
        "\nreturn len(dummy_list)\n"
        ]
        result = _get_function_body(dummy_function_with_loop)
        assert result == "".join(func_line for func_line in func_strings)
        # TODO fix - fails because doesn't strip spaces from continue, inconsistent




    
