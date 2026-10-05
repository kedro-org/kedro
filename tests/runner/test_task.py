from functools import wraps

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
        catalog["result"] = fake_dataset
        n = node(generate_one, inputs=None, outputs="result")

        with pytest.raises(Exception, match="nodes wrapping generator functions"):
            task = Task(
                node=n,
                catalog=catalog,
                hook_manager=_NullPluginManager(),
                is_async=True,
            )
            task.execute()

    def test_wrapped_generator_fails_async(self, catalog):
        @wraps(generate_one)
        def wrapped(*args, **kwargs):
            return generate_one(*args, **kwargs)

        n = node(wrapped, inputs=None, outputs="result")
        with pytest.raises(ValueError, match="nodes wrapping generator functions"):
            Task(
                node=n,
                catalog=catalog,
                hook_manager=_NullPluginManager(),
                is_async=True,
            ).execute()

    def test_wrapper_that_consumes_the_generator_still_runs_async(
        self, mocker, catalog
    ):
        fake_dataset = mocker.Mock()
        mocker.patch.object(catalog, "get", return_value=fake_dataset)

        @wraps(generate_one)
        def wrapped(*args, **kwargs):
            return list(generate_one(*args, **kwargs))

        n = node(wrapped, inputs=None, outputs="result")
        Task(
            node=n,
            catalog=catalog,
            hook_manager=_NullPluginManager(),
            is_async=True,
        ).execute()
        assert fake_dataset.save.call_args_list == [((list(range(10)),),)]

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
        run_id = "fake_run_id"
        package_name = mocker.sentinel.package_name

        task = Task(
            node=node_,
            catalog=catalog,
            run_id=run_id,
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
    def test_forkserver_bootstraps_subprocess(
        self,
        mock_logging,
        mock_configure_project,
        is_async,
        mocker,
    ):
        mocker.patch("multiprocessing.get_start_method", return_value="forkserver")
        node_ = mocker.sentinel.node
        catalog = mocker.sentinel.catalog
        run_id = "fake_run_id"
        package_name = mocker.sentinel.package_name

        task = Task(
            node=node_,
            catalog=catalog,
            run_id=run_id,
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
        run_id = "fake_run_id"
        package_name = mocker.sentinel.package_name

        task = Task(
            node=node_,
            catalog=catalog,
            run_id=run_id,
            is_async=is_async,
            parallel=True,
        )
        task._run_node_synchronization(package_name=package_name)
        mock_logging.assert_not_called()

    def test_raise_task_exception(self, mocker):
        node_ = mocker.sentinel.node
        catalog = mocker.sentinel.catalog
        run_id = "fake_run_id"

        with pytest.raises(TaskError, match="No hook_manager provided."):
            task = Task(
                node=node_,
                catalog=catalog,
                is_async=False,
                run_id=run_id,
                parallel=False,
            )
            task.execute()
