"""``SequentialRunner`` is an ``AbstractRunner`` implementation. It can be
used to run the ``Pipeline`` in a sequential manner using a topological sort
of provided nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro.runner.runner import AbstractRunner

if TYPE_CHECKING:
    from pluggy import PluginManager

    from kedro.io import CatalogProtocol
    from kedro.pipeline import Pipeline


class SequentialRunner(AbstractRunner):
    """``SequentialRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in a sequential manner using a
    topological sort of provided nodes.
    """

    def __init__(
        self,
        is_async: bool = False,
    ):
        """Instantiates the runner class.

        Args:
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.
        """
        super().__init__(is_async=is_async)

    def _get_executor(self, max_workers: int) -> None:
        return None

    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluginManager | None = None,
        run_id: str | None = None,
    ) -> None:
        """The method implementing sequential pipeline running.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            run_id: The id of the run.

        Raises:
            Exception: in case of any downstream node failure.
        """
        if not self._is_async:
            self._logger.info(
                "Using synchronous mode for loading and saving data. Use the --async flag "
                "for potential performance gains. https://docs.kedro.org/en/stable/nodes_and_pipelines/run_a_pipeline.html#load-and-save-asynchronously"
            )
        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            hook_manager=hook_manager,
            run_id=run_id,
        )
