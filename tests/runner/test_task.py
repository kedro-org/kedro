import pytest

from kedro.framework.hooks.manager import _NullPluginManager
from kedro.pipeline import node
from kedro.runner import Task
from kedro.runner.task import TaskError


def generate_one():
    yield from range(10)


class TestTask:
    @pytest.fixture(autouse=True)
    def mock_logging(self, mocker):
        return mocker.patch("logging.config.dictConfig")

    @pytest.fixture
    def mock_configure_project(self, mocker):
        return mocker.patch("kedro.framework.project.configure_project")

    def test_generator_fail_async(self, mocker, catalog):
        fake_dataset = mocker.Mock()
        catalog.add("result", fake_dataset)
        n = node(generate_one, inputs=None, outputs="result")

        with pytest.raises(Exception, match="nodes wrapping generator functions"):
            task = Task(
                node=n,
                catalog=catalog,
                hook_manager=_NullPluginManager(),
                is_async=True,
            )
            task.execute()

    @pytest.mark.parametrize("is_async", [False, True])
    def test_package_name_and_logging_provided(
        self,
        mock_logging,
        mock_configure_project,
        is_async,
        mocker,
    ):
        mocker.patch("multiprocessing.get_start_method", return_value="spawn")
        node_ = mocker.sentinel.node
        catalog = mocker.sentinel.catalog
        session_id = "fake_session_id"
        package_name = mocker.sentinel.package_name

        task = Task(
            node=node_,
            catalog=catalog,
            session_id=session_id,
            is_async=is_async,
            parallel=True,
        )
        task._run_node_synchronization(
            package_name=package_name,
            logging_config={"fake_logging_config": True},
        )
        mock_logging.assert_called_once_with({"fake_logging_config": True})
        mock_configure_project.assert_called_once_with(package_name)

    @pytest.mark.parametrize("is_async", [False, True])
    def test_package_name_not_provided(self, mock_logging, is_async, mocker):
        mocker.patch("multiprocessing.get_start_method", return_value="fork")
        node_ = mocker.sentinel.node
        catalog = mocker.sentinel.catalog
        session_id = "fake_session_id"
        package_name = mocker.sentinel.package_name

        task = Task(
            node=node_,
            catalog=catalog,
            session_id=session_id,
            is_async=is_async,
            parallel=True,
        )
        task._run_node_synchronization(package_name=package_name)
        mock_logging.assert_not_called()

    def test_raise_task_exception(self, mocker):
        node_ = mocker.sentinel.node
        catalog = mocker.sentinel.catalog
        session_id = "fake_session_id"

        with pytest.raises(TaskError, match="No hook_manager provided."):
            task = Task(
                node=node_,
                catalog=catalog,
                is_async=False,
                session_id=session_id,
                parallel=False,
            )
            task.execute()
