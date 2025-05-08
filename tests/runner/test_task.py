from unittest.mock import AsyncMock, MagicMock

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

    @pytest.mark.asyncio
    async def test_run_node_async(self, mocker):
        """Test that `_run_node_async` properly loads inputs, executes the node, and saves outputs asynchronously."""
        catalog = mocker.sentinel.catalog
        session_id = "fake_session_id"
        hook_manager = _NullPluginManager()
        fake_dataset = mocker.Mock()
        node_ = mocker.sentinel.node

        # Create an async mock for dataset load/save
        mock_async_dataset_load = mocker.patch(
            "kedro.runner.task.Task._async_dataset_load",
            new_callable=AsyncMock,
            return_value=fake_dataset,
        )
        mock_async_dataset_save = mocker.patch(
            "kedro.runner.task.Task._async_dataset_save", new_callable=AsyncMock
        )
        mock_collect_inputs_from_hook = mocker.patch(
            "kedro.runner.task.Task._collect_inputs_from_hook",
            return_value={"input3": fake_dataset},
        )
        mock_call_node_run = mocker.patch(
            "kedro.runner.task.Task._call_node_run",
            return_value={"output1": fake_dataset, "output2": fake_dataset},
        )

        # Mock inputs
        node_.inputs = {"input1": fake_dataset, "input2": fake_dataset}

        # Call the function
        await Task(
            node=node_,
            catalog=catalog,
            is_async=True,
            hook_manager=hook_manager,
            session_id=session_id,
        )._run_node_async(node_, catalog, hook_manager, session_id)

        # Assert inputs were loaded
        assert mock_async_dataset_load.call_count == len(node_.inputs)
        assert mock_async_dataset_load.await_count == len(node_.inputs)
        mock_collect_inputs_from_hook.assert_called_once_with(
            node_, catalog, node_.inputs, True, hook_manager, session_id=session_id
        )

        updated_inputs = node_.inputs.copy()
        updated_inputs.update(mock_collect_inputs_from_hook.return_value)

        mock_call_node_run.assert_called_once_with(
            node_, catalog, updated_inputs, True, hook_manager, session_id=session_id
        )
        assert mock_async_dataset_save.call_count == len(
            mock_call_node_run.return_value
        )
        assert mock_async_dataset_save.await_count == len(
            mock_call_node_run.return_value
        )

    @pytest.mark.asyncio
    async def test_async_dataset_load(self, mocker):
        """Test that `_async_dataset_load` calls hooks and loads data in the proper order."""
        catalog = mocker.sentinel.catalog
        hook_manager = _NullPluginManager()
        dataset_name = "test_dataset"
        node_ = mocker.sentinel.node

        # Create an order log list
        call_order = []

        # Set side_effects on hooks and catalog.load to log when they're called
        def before_hook(*args, **kwargs):
            call_order.append("before")

        def after_hook(*args, **kwargs):
            call_order.append("after")

        def load_side_effect(*args, **kwargs):
            call_order.append("load")
            return "test_data"

        catalog.load = MagicMock(side_effect=load_side_effect)
        hook_manager.hook.before_dataset_loaded = MagicMock(side_effect=before_hook)
        hook_manager.hook.after_dataset_loaded = MagicMock(side_effect=after_hook)

        data = await Task._async_dataset_load(
            dataset_name, node_, catalog, hook_manager
        )

        assert call_order == ["before", "load", "after"]
        hook_manager.hook.before_dataset_loaded.assert_called_once_with(
            dataset_name=dataset_name, node=node_
        )
        assert data == "test_data"
        hook_manager.hook.after_dataset_loaded.assert_called_once_with(
            dataset_name=dataset_name, data="test_data", node=node_
        )

    @pytest.mark.asyncio
    async def test_async_dataset_save(self, mocker):
        """Test that _async_dataset_save calls hooks and saves data in the proper order."""
        # Setup test objects
        catalog = mocker.sentinel.catalog
        hook_manager = _NullPluginManager()
        dataset_name = "test_dataset"
        data = {"key": "value"}
        node_ = mocker.sentinel.node

        # Create a list to log call order
        call_order = []

        # Define side effects to log when each function is called
        def before_hook(*args, **kwargs):
            call_order.append("before")

        def after_hook(*args, **kwargs):
            call_order.append("after")

        def save_side_effect(*args, **kwargs):
            call_order.append("save")

        catalog.save = MagicMock(side_effect=save_side_effect)
        hook_manager.hook.before_dataset_saved = MagicMock(side_effect=before_hook)
        hook_manager.hook.after_dataset_saved = MagicMock(side_effect=after_hook)

        await Task._async_dataset_save(dataset_name, data, node_, catalog, hook_manager)

        assert call_order == ["before", "save", "after"]
        hook_manager.hook.before_dataset_saved.assert_called_once_with(
            dataset_name=dataset_name, data=data, node=node_
        )
        catalog.save.assert_called_once_with(dataset_name, data)
        hook_manager.hook.after_dataset_saved.assert_called_once_with(
            dataset_name=dataset_name, data=data, node=node_
        )
