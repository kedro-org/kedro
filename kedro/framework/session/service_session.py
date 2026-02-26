

from copy import deepcopy
import getpass
import os
from typing import Iterable
import click
from kedro import logging
from kedro.config.abstract_config import AbstractConfigLoader
from kedro.framework.context.context import KedroContext
from kedro.framework.hooks.manager import _create_hook_manager, _register_hooks, _register_hooks_entry_points
from kedro.framework.session.abstract_session import AbstractSession
from pathlib import Path
from kedro.framework.project import settings, validate_settings, pipelines
from kedro.framework.session.session import KedroSessionError, _describe_git, _jsonify_cli_context
from kedro.framework.session.store import BaseSessionStore
from kedro.io.core import generate_timestamp
from kedro.io.data_catalog import SharedMemoryDataCatalog
from kedro.pipeline.pipeline import Pipeline
from kedro.runner.parallel_runner import ParallelRunner
from kedro.runner.runner import AbstractRunner
import uuid
from kedro import __version__ as kedro_version

from kedro.runner.sequential_runner import SequentialRunner

class KedroServiceSession(AbstractSession):
    """"""

    def __init__(
            self,
            session_id: str,
            package_name: str | None = None,
            project_path: Path | str | None = None,
            save_on_close: bool = False,
            conf_source: str | None = None,
    ):
        super().__init__(
            session_id=session_id,
            package_name=package_name,
            project_path=project_path,
            save_on_close=save_on_close,
            conf_source=conf_source,
        )
        hook_manager = _create_hook_manager()
        _register_hooks(hook_manager, settings.HOOKS)
        _register_hooks_entry_points(hook_manager, settings.DISABLE_HOOKS_FOR_PLUGINS)
        self._hook_manager = hook_manager

        self._conf_source = conf_source or str(
            self._project_path / settings.CONF_SOURCE
        )
        self.results = {}
        # self._context = self.load_context()

    def load_context(self, runtime_params) -> KedroContext:
        """An instance of the project context."""
        env = self.store.get("env")
        # runtime_params = self.store.get("runtime_params")
        config_loader = self._get_config_loader(runtime_params)
        context_class = settings.CONTEXT_CLASS
        context = context_class(
            package_name=self._package_name,
            project_path=self._project_path,
            config_loader=config_loader,
            env=env,
            runtime_params=runtime_params,
            hook_manager=self._hook_manager,
        )
        self._hook_manager.hook.after_context_created(context=context)
        print(context.params)
        return context  

    def _get_config_loader(self, runtime_params) -> AbstractConfigLoader:
        """An instance of the config loader."""
        env = self.store.get("env")
        # runtime_params = self.store.get("runtime_params")

        config_loader_class = settings.CONFIG_LOADER_CLASS
        return config_loader_class(  # type: ignore[no-any-return]
            conf_source=self._conf_source,
            env=env,
            runtime_params=runtime_params,
            **settings.CONFIG_LOADER_ARGS,
        )

    @classmethod
    def create(
        cls,
        project_path: Path | str | None = None,
        save_on_close: bool = True,
        env: str | None = None,
        conf_source: str | None = None,
    ) -> "KedroServiceSession":
        """Create a new KedroSession for the given project path and environment.

        Args:
            project_path: Path to the Kedro project. If not provided, the current
                working directory is used.
            save_on_close: Whether to save the session automatically when it is closed.
            env: The Kedro environment to use. If not provided, the default environment
                is used.
            conf_source: Optional path to configuration source. If not provided, it will
                default to the "conf" directory in the project path.

        Returns:
            A new instance of KedroSession.
        """
        validate_settings()
        session = cls(
            project_path=project_path,
            session_id=generate_timestamp(),
            save_on_close=save_on_close,
            conf_source=conf_source,
        )

        session_data = {
            "project_path": session._project_path,
            "session_id": session.session_id,
        }
        ctx = click.get_current_context(silent=True)
        if ctx:
            session_data["cli"] = _jsonify_cli_context(ctx)

        env = env or os.getenv("KEDRO_ENV")
        if env:
            session_data["env"] = env

        try:
            session_data["username"] = getpass.getuser()
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Unable to get username. Full exception: %s", exc
            )

        session_data.update(**_describe_git(session._project_path))
        session._store.update(session_data)
        return session


    def _init_store(self) -> BaseSessionStore:
        store_class = settings.SESSION_STORE_CLASS
        classpath = f"{store_class.__module__}.{store_class.__qualname__}"
        store_args = deepcopy(settings.SESSION_STORE_ARGS)
        store_args.setdefault("path", (self._project_path / "sessions").as_posix())
        store_args["session_id"] = self.session_id

        try:
            return store_class(**store_args)  # type: ignore[no-any-return]
        except TypeError as err:
            raise ValueError(
                f"\n{err}.\nStore config must only contain arguments valid "
                f"for the constructor of '{classpath}'."
            ) from err
        except Exception as err:
            raise ValueError(
                f"\n{err}.\nFailed to instantiate session store of type '{classpath}'."
            ) from err


    def run(
        self,
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
        runtime_params: dict[str, str] | None = None,
    ):
        project_name = self._package_name or self._project_path.name
        self._logger.info("Kedro project %s", project_name)
        run_id = str(uuid.uuid4())
        session_id = self.store["session_id"]
        self._logger.info("Session ID %s, run ID %s", session_id, run_id)
        save_version = session_id + "_" + run_id

        combined_pipelines = Pipeline([])
        for name in pipeline_names or ["__default__"]:
            try:
                combined_pipelines += pipelines[name]
            except KeyError as exc:
                raise ValueError(
                    f"Failed to load pipeline {name}"
                ) from exc
        print("runtime_params", runtime_params)
        context = self.load_context(runtime_params)
        filtered_pipeline = combined_pipelines.filter(
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
                "KedroSession expect an instance of Runner instead of a class."
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
            "session_id": session_id,
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

        hook_manager = self._hook_manager
        hook_manager.hook.before_pipeline_run(
            run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
        )
        try:
            run_result = runner.run(
                filtered_pipeline,
                catalog,
                hook_manager,
                run_id=session_id,
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

        self.results.update({run_id: run_result})
        return run_result