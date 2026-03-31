from __future__ import annotations

import logging
import logging.config
import traceback
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kedro import __version__ as kedro_version
from kedro.framework import project as kedro_project
from kedro.framework.hooks import _create_hook_manager
from kedro.framework.hooks.manager import _register_hooks, _register_hooks_entry_points
from kedro.framework.project import (
    pipelines,
    settings,
    validate_settings,
)
from kedro.io.core import generate_timestamp
from kedro.io.data_catalog import SharedMemoryDataCatalog
from kedro.pipeline.pipeline import Pipeline
from kedro.runner import AbstractRunner, ParallelRunner, SequentialRunner
from kedro.utils import find_kedro_project

from .abstract_session import AbstractSession, KedroSessionError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from kedro.config import AbstractConfigLoader
    from kedro.framework.context import KedroContext


class KedroServiceSession(AbstractSession):
    """
    KedroServiceSession offers a session implementation that allows for multiple runs and data injection.
    """

    def __init__(
        self,
        session_id: str,
        package_name: str | None = None,
        project_path: Path | str | None = None,
        conf_source: Path | str | None = None,
        env: str | None = None,
    ):
        self._project_path = Path(
            project_path or find_kedro_project(Path.cwd()) or Path.cwd()
        ).resolve()
        self.session_id = session_id
        self._package_name = package_name or kedro_project.PACKAGE_NAME
        hook_manager = _create_hook_manager()
        _register_hooks(hook_manager, settings.HOOKS)
        _register_hooks_entry_points(hook_manager, settings.DISABLE_HOOKS_FOR_PLUGINS)
        self._hook_manager = hook_manager
        self.env = env
        self._conf_source = conf_source or str(
            self._project_path / settings.CONF_SOURCE
        )

    @classmethod
    def create(
        cls,
        session_id: str | None = None,
        project_path: Path | str | None = None,
        env: str | None = None,
        conf_source: Path | str | None = None,
    ) -> KedroServiceSession:
        """Create a new instance of the session."""
        validate_settings()

        session = cls(
            project_path=project_path,
            session_id=session_id or uuid.uuid4(),
            conf_source=conf_source,
            env=env,
        )
        return session

    def _log_exception(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        type_ = [] if exc_type.__module__ == "builtins" else [exc_type.__module__]
        type_.append(exc_type.__qualname__)

        exc_data = {
            "type": ".".join(type_),
            "value": str(exc_value),
            "traceback": traceback.format_tb(exc_tb),
        }
        self._logger.debug("Service session exception: %s", exc_data)

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def __enter__(self) -> KedroServiceSession:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, tb_: Any) -> None:
        if exc_type:
            self._log_exception(exc_type, exc_value, tb_)
        self.close()

    def close(self) -> None:
        self._logger.info("Closing session %s", self.session_id)

    def _get_config_loader(
        self, runtime_params: dict[str, Any] | None = None
    ) -> AbstractConfigLoader:
        """An instance of the config loader."""
        config_loader_class = settings.CONFIG_LOADER_CLASS
        return config_loader_class(  # type: ignore[no-any-return]
            conf_source=self._conf_source,
            env=self.env,
            runtime_params=runtime_params,
            **settings.CONFIG_LOADER_ARGS,
        )

    def load_context(
        self, runtime_params: dict[str, Any] | None = None
    ) -> KedroContext:
        """An instance of the project context."""
        config_loader = self._get_config_loader(runtime_params)
        context_class = settings.CONTEXT_CLASS
        context = context_class(
            package_name=self._package_name,
            project_path=self._project_path,
            config_loader=config_loader,
            env=self.env,
            runtime_params=runtime_params,
            hook_manager=self._hook_manager,
        )
        self._hook_manager.hook.after_context_created(context=context)

        return context  # type: ignore[no-any-return]

    def run(  # noqa: PLR0913
        self,
        run_id: str | None = None,
        pipeline_names: list[str] | None = None,
        tags: Iterable[str] | None = None,
        runner: AbstractRunner | None = None,
        node_names: Iterable[str] | None = None,
        from_nodes: Iterable[str] | None = None,
        to_nodes: Iterable[str] | None = None,
        from_inputs: Iterable[str] | None = None,
        to_outputs: Iterable[str] | None = None,
        load_versions: dict[str, str] | None = None,
        namespaces: Iterable[str] | None = None,
        only_missing_outputs: bool = False,
        runtime_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline."""
        run_id = run_id or generate_timestamp()
        project_name = self._package_name or self._project_path.name
        self._logger.info("Kedro project %s", project_name)
        self._logger.info("Session ID: %s", self.session_id)
        self._logger.info("Run ID: %s", run_id)
        save_version = run_id

        context = self.load_context(runtime_params)
        pipeline_names = pipeline_names or ["__default__"]
        combined_pipeline = Pipeline([])
        for name in pipeline_names:
            try:
                combined_pipeline += pipelines[name]
            except KeyError as exc:
                raise ValueError(
                    f"Failed to find the pipeline named '{name}'. "
                    f"It needs to be generated and returned "
                    f"by the 'register_pipelines' function."
                ) from exc

        filtered_pipeline = combined_pipeline.filter(
            tags=tags,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            node_names=node_names,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            node_namespaces=namespaces,
        )
        runner = runner or SequentialRunner()
        if not isinstance(runner, AbstractRunner):
            raise KedroSessionError(
                "KedroServiceSession expect an instance of Runner instead of a class."
                "Have you forgotten the `()` at the end of the statement?"
            )

        catalog_class = (
            SharedMemoryDataCatalog
            if isinstance(runner, ParallelRunner)
            else settings.DATA_CATALOG_CLASS
        )

        catalog = context._get_catalog(
            catalog_class=catalog_class,
            save_version=save_version,
            load_versions=load_versions,
        )

        record_data = {
            "session_id": self.session_id,
            "run_id": run_id,
            "project_path": self._project_path.as_posix(),
            "env": context.env,
            "kedro_version": kedro_version,
            "tags": tags,
            "from_nodes": from_nodes,
            "to_nodes": to_nodes,
            "node_names": node_names,
            "from_inputs": from_inputs,
            "to_outputs": to_outputs,
            "load_versions": load_versions,
            "runtime_params": runtime_params,
            "pipeline_names": pipeline_names,
            "namespaces": namespaces,
            "runner": getattr(runner, "__name__", str(runner)),
            "only_missing_outputs": only_missing_outputs,
        }

        # Run the runner
        hook_manager = self._hook_manager
        hook_manager.hook.before_pipeline_run(
            run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
        )
        try:
            run_result = runner.run(
                filtered_pipeline,
                catalog,
                hook_manager,
                run_id=run_id,
                only_missing_outputs=only_missing_outputs,
            )
        except Exception as error:
            hook_manager.hook.on_pipeline_error(
                error=error,
                run_params=record_data,
                pipeline=filtered_pipeline,
                catalog=catalog,
            )
            raise

        hook_manager.hook.after_pipeline_run(
            run_params=record_data,
            run_result=run_result,
            pipeline=filtered_pipeline,
            catalog=catalog,
        )
        return run_result
