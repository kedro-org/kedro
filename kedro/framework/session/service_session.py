from __future__ import annotations

import logging
import logging.config
import os
import textwrap
import threading
import uuid
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from kedro import __version__ as kedro_version
from kedro.config.lazy_omegaconf_config import LazyOmegaConfigLoader
from kedro.config.omegaconf_config import OmegaConfigLoader
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
from kedro.utils import experimental, find_kedro_project, get_close_matches

from .abstract_session import AbstractSession, KedroSessionError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from contextlib import AbstractContextManager

    from kedro.config import AbstractConfigLoader
    from kedro.framework.context import KedroContext
    from kedro.io import CatalogProtocol

# Process-wide because OmegaConf's resolver registry is process-global: loaders
# other than ``LazyOmegaConfigLoader`` replace the ``runtime_params`` resolver
# without locking, so concurrent runs must not load their configuration at once.
_CONFIG_LOADING_LOCK = threading.RLock()


@experimental
class KedroServiceSession(AbstractSession):
    """``KedroServiceSession`` is the object that is responsible for managing the lifecycle
    of multiple Kedro runs. Use `KedroServiceSession.create()` as
    a context manager to construct a new KedroServiceSession with session data
    provided (see the example below).



    Example:
    ``` python
    from kedro.framework.session import KedroServiceSession
    from kedro.framework.startup import bootstrap_project
    from pathlib import Path

    # If you are creating a session outside of a Kedro project (i.e. not using
    # `kedro run` or `kedro jupyter`), you need to run `bootstrap_project` to
    # let Kedro find your configuration.
    bootstrap_project(Path("<project_root>"))
    with KedroServiceSession.create() as session:
        run_1 = session.run(runtime_params={"param1": "value1"})
        run_2 = session.run(runtime_params={"param1": "value2"})
        # Inject ad-hoc data for this run only, without touching catalog config
        run_3 = session.run(runtime_datasets={"input_df": some_dataframe})
    ```
    NOTE: This session implementation is under active development and may occasionally contain breaking changes.
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
        self._serving_mode = False
        self._shared_config_loader: LazyOmegaConfigLoader | None = None

    @classmethod
    def create(
        cls,
        session_id: str | None = None,
        project_path: Path | str | None = None,
        env: str | None = None,
        conf_source: Path | str | None = None,
        serving_mode: bool = False,
    ) -> KedroServiceSession:
        """Create a new instance of the session.

        If ``CONFIG_LOADER_CLASS`` is ``LazyOmegaConfigLoader`` (or a subclass),
        the session creates one loader and preloads its configuration files.
        Each run then resolves configuration with a loader copy from
        ``with_runtime_params()``, so files are read only once per session.
        Other loaders are created for each run, and their concurrent run setup
        is serialised. This lock does not protect unrelated configuration
        operations.

        Args:
            session_id: Optional ID for this session; defaults to a UUID.
            project_path: Optional path to the Kedro project root.
            env: Optional Kedro environment name.
            conf_source: Optional path to the configuration source directory.
            serving_mode: When ``True``, all pipelines are preloaded eagerly at
                session creation time, making pipeline lookups safe across
                concurrent ``run()`` calls, and ``runtime_params`` are treated
                as untrusted. Leave ``False`` (the default) for CLI use. If
                ``CONFIG_LOADER_CLASS`` isn't ``LazyOmegaConfigLoader``, the
                session logs a warning about the safety and performance
                implications of concurrent runs.

        Returns:
            A new ``KedroServiceSession`` instance ready for use.
        """
        validate_settings()
        env = env or os.getenv("KEDRO_ENV")
        session = cls(
            project_path=project_path,
            session_id=session_id or str(uuid.uuid4()),
            conf_source=conf_source,
            env=env,
        )
        session._preload_shared_config_loader()
        if serving_mode:
            session._enable_serving_mode()
        return session

    def _preload_shared_config_loader(self) -> None:
        """Create the session's ``LazyOmegaConfigLoader`` and preload its files.

        A new instance of any other loader is created for each run.
        """
        if not issubclass(settings.CONFIG_LOADER_CLASS, LazyOmegaConfigLoader):
            return
        self._logger.info("Preloading configuration for session %s", self.session_id)
        config_loader = cast("LazyOmegaConfigLoader", self._new_config_loader())
        config_loader.preload()
        self._shared_config_loader = config_loader

    def _enable_serving_mode(self) -> None:
        """Preload all pipelines, then switch the session into serving mode.

        The flag is set *after* a successful preload so that a failure during
        loading leaves the session in normal CLI mode rather than in an
        inconsistent state where ``run()`` would skip ``set_requested()``
        against an empty pipeline registry.
        """
        self._warn_if_type_selection_restriction_is_overridden()
        self._warn_if_config_loader_is_not_lazy()
        self._preload_pipelines()
        self._serving_mode = True

    def _warn_if_config_loader_is_not_lazy(self) -> None:
        """Explain the safety and performance cost of concurrent runs without
        ``LazyOmegaConfigLoader``, the only loader that isolates them on its own."""
        config_loader_class = settings.CONFIG_LOADER_CLASS
        if issubclass(config_loader_class, LazyOmegaConfigLoader):
            return
        name = config_loader_class.__name__
        message = (
            f"`CONFIG_LOADER_CLASS` is `{name}`, not `LazyOmegaConfigLoader`. "
            "With concurrent `run()` calls:\n"
            "- Safety: Kedro loads each run's configuration while holding a "
            "process-wide lock, so runtime parameters stay isolated during run "
            "setup. Configuration resolved elsewhere at the same time, for "
            "example by hooks after the catalog is created, by nodes, or by "
            "another config loader such as the one `GET /snapshot` creates in the "
            "HTTP server, isn't protected: one run's runtime parameters can then "
            "leak into another run.\n"
            "- Performance: every run rereads the configuration files, and "
            "concurrent runs set up one at a time.\n"
        )
        if not issubclass(config_loader_class, OmegaConfigLoader):
            message += (
                f"- Security: Kedro can't make `{name}` reject dataset types "
                "selected through runtime parameters.\n"
            )
        message += (
            "To cache configuration and resolve runs concurrently, set "
            "`CONFIG_LOADER_CLASS = LazyOmegaConfigLoader` in `settings.py`."
        )
        self._logger.warning(message)

    def _warn_if_type_selection_restriction_is_overridden(self) -> None:
        """Warn that serving mode ignores a disabled type-selection restriction."""
        if issubclass(settings.CONFIG_LOADER_CLASS, OmegaConfigLoader) and (
            settings.CONFIG_LOADER_ARGS.get("restrict_runtime_params_type_selection")
            is False
        ):
            self._logger.warning(
                "Serving mode overrides `restrict_runtime_params_type_selection` "
                "from `CONFIG_LOADER_ARGS` to True."
            )

    def _preload_pipelines(self) -> None:
        """Eagerly load all registered pipelines into the shared singleton.

        Called once during session creation in serving mode, before any request
        threads are started. After this returns, ``pipelines._content`` is
        fully populated and ``pipelines._is_data_loaded`` is ``True``, so
        subsequent concurrent ``run()`` calls read the dict without mutating
        shared state.
        """
        self._logger.info(
            "Serving mode: preloading all pipelines for session %s", self.session_id
        )
        pipelines.set_requested(None)
        list(pipelines)

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def close(self) -> None:
        self._logger.info("Closing session %s", self.session_id)

    def _get_config_loader(
        self,
        runtime_params: dict[str, Any] | None = None,
    ) -> AbstractConfigLoader:
        """An instance of the config loader.

        Args:
            runtime_params: Extra parameters passed to a Kedro run.

        In serving mode, ``runtime_params`` can originate from an untrusted
        caller. OmegaConfigLoader subclasses are forced to reject catalog
        dataset types selected through runtime parameters, regardless of
        ``CONFIG_LOADER_ARGS``. See https://github.com/kedro-org/kedro/issues/5706.

        With ``LazyOmegaConfigLoader`` (or a subclass), the returned loader is a
        copy of the session's preloaded loader, in every mode. It shares the
        cached files and resolves them with ``runtime_params``. Other loaders
        are created for each call. In serving mode, only ``OmegaConfigLoader``
        subclasses receive the restriction: Kedro can't enforce it for other
        loaders.
        """
        if self._shared_config_loader is not None:
            return self._shared_config_loader.with_runtime_params(
                runtime_params,
                restrict_runtime_params_type_selection=(
                    True if self._serving_mode else None
                ),
            )
        return self._new_config_loader(
            runtime_params, restrict_type_selection=self._serving_mode
        )

    def _new_config_loader(
        self,
        runtime_params: dict[str, Any] | None = None,
        *,
        restrict_type_selection: bool = False,
    ) -> AbstractConfigLoader:
        """Create a loader from ``CONFIG_LOADER_CLASS`` and ``CONFIG_LOADER_ARGS``."""
        config_loader_class = settings.CONFIG_LOADER_CLASS
        config_loader_args = dict(settings.CONFIG_LOADER_ARGS)
        if restrict_type_selection and issubclass(
            config_loader_class, OmegaConfigLoader
        ):
            config_loader_args["restrict_runtime_params_type_selection"] = True
        return config_loader_class(  # type: ignore[no-any-return]
            conf_source=self._conf_source,
            env=self.env,
            runtime_params=runtime_params,
            **config_loader_args,
        )

    def _config_loading_scope(self) -> AbstractContextManager[Any]:
        """Serialise run setup unless the loader isolates its own resolvers."""
        if self._shared_config_loader is None:
            return _CONFIG_LOADING_LOCK
        return nullcontext()

    def load_context(
        self,
        runtime_params: dict[str, Any] | None = None,
    ) -> KedroContext:
        """An instance of the project context with runtime parameters injected."""
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
        runtime_datasets: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Runs the pipeline with a specified runner.

        Args:
            run_id: An optional identifier for this run, also used as the save
                version. Defaults to a generated timestamp.
            pipeline_names: Name of the pipelines that is being run. Defaults
                to ``["__default__"]``.
            tags: An optional list of node tags which should be used to
                filter the nodes of the ``Pipeline``. If specified, only the nodes
                containing *any* of these tags will be run.
            runner: An optional parameter specifying the runner that you want to run
                the pipeline with. Defaults to ``SequentialRunner``.
            node_names: An optional list of node names which should be used to
                filter the nodes of the ``Pipeline``. If specified, only the nodes
                with these names will be run.
            from_nodes: An optional list of node names which should be used as a
                starting point of the new ``Pipeline``.
            to_nodes: An optional list of node names which should be used as an
                end point of the new ``Pipeline``.
            from_inputs: An optional list of input datasets which should be
                used as a starting point of the new ``Pipeline``.
            to_outputs: An optional list of output datasets which should be
                used as an end point of the new ``Pipeline``.
            load_versions: An optional flag to specify a particular dataset
                version timestamp to load.
            namespaces: The namespaces of the nodes that are being run.
            only_missing_outputs: Run only nodes with missing outputs.
            runtime_params: Optional parameters for this run only, used to
                resolve ``runtime_params`` interpolation and passed through
                parameter validation.
            runtime_datasets: Optional mapping of dataset name to value, injected
                into this run's catalog immediately before execution. Each
                value is either raw data (wrapped in a ``MemoryDataset``) or an
                ``AbstractDataset`` instance (stored directly). Only free inputs
                of the pipeline being run can be injected; parameters must be
                passed through ``runtime_params``. An existing catalog entry
                with the same name is replaced for this run only, and any
                validator declared for it is applied to the injected data.
                With ``ParallelRunner``, injected values are only read by
                worker processes, so they must be serialisable.
        Raises:
            ValueError: If a requested pipeline is not defined by
                `register_pipelines`.
            KedroSessionError: If `runner` is not a runner instance, or if
                `runtime_datasets` contains parameters or names that are not
                free inputs of the pipeline being run.
            Exception: Any uncaught exception during the run will be re-raised
                after being passed to ``on_pipeline_error`` hook.
        Returns:
            Dictionary with pipeline outputs, where keys are dataset names
            and values are dataset objects.
        """
        run_id = run_id or generate_timestamp()
        project_name = self._package_name or self._project_path.name
        self._logger.info("Kedro project %s", project_name)
        self._logger.info("Session ID: %s", self.session_id)
        self._logger.info("Run ID: %s", run_id)
        save_version = run_id

        # In CLI mode, set_requested() tells the lazy loader which pipelines to
        # import, keeping startup fast when only one pipeline is needed.
        # In serving mode all pipelines are already loaded, so skip the write
        # to avoid mutating shared singleton state across concurrent requests.
        if not self._serving_mode:
            pipelines.set_requested(pipeline_names or None)
        # Loaders other than LazyOmegaConfigLoader resolve configuration with
        # process-global resolvers, so run setup is serialised for them.
        with self._config_loading_scope():
            context = self.load_context(runtime_params)
            pipeline_names = pipeline_names or ["__default__"]
            combined_pipeline = Pipeline([])
            for name in pipeline_names:
                try:
                    combined_pipeline += pipelines[name]
                except KeyError as exc:
                    if not self._serving_mode:
                        # Reset to None so keys() loads all pipelines for suggestions.
                        pipelines.set_requested(None)
                    matches = get_close_matches(name, pipelines.keys())
                    if matches:
                        suggestion = (
                            "Did you mean one of these instead?\n"
                            + textwrap.indent("\n".join(matches), " " * 4)
                        )
                    else:
                        suggestion = ""
                    raise ValueError(
                        f"Failed to find the pipeline named '{name}'. "
                        f"It needs to be generated and returned "
                        f"by the 'register_pipelines' function. "
                        f"{suggestion}"
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
            if runtime_datasets:
                _check_runtime_dataset_names(runtime_datasets, filtered_pipeline)

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

            # Scope validation to the requested pipelines; `__default__` falls
            # back to validating every registered pipeline.
            if "__default__" not in pipeline_names:
                context._pipelines_to_validate = list(pipeline_names)

            catalog = context._get_catalog(
                catalog_class=catalog_class,
                save_version=save_version,
                load_versions=load_versions,
            )

        if runtime_datasets:
            _inject_runtime_datasets(catalog, runtime_datasets)

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
            "runtime_params": runtime_params or {},
            "runtime_datasets": list((runtime_datasets or {}).keys()),
            "pipeline_names": pipeline_names,
            "namespaces": namespaces,
            "runner": runner.__class__.__name__,
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


def _check_runtime_dataset_names(
    runtime_datasets: dict[str, Any], pipeline: Pipeline
) -> None:
    """Only allow free inputs of the pipeline being run to be injected.

    Parameters are rejected so they cannot bypass parameter validation, and
    intermediate or output datasets are rejected so a caller cannot skip
    upstream nodes or silently replace persisted outputs.
    """
    param_names = sorted(
        name
        for name in runtime_datasets
        if name == "parameters" or name.startswith("params:")
    )
    if param_names:
        raise KedroSessionError(
            f"Cannot inject parameters as runtime datasets: {param_names}. "
            "Pass parameters through runtime params instead."
        )

    not_free_inputs = sorted(set(runtime_datasets) - pipeline.inputs())
    if not_free_inputs:
        raise KedroSessionError(
            f"Only free inputs of the pipeline being run can be injected as "
            f"runtime datasets, but got: {not_free_inputs}."
        )


def _inject_runtime_datasets(
    catalog: CatalogProtocol, runtime_datasets: dict[str, Any]
) -> None:
    """Inject runtime datasets into the catalog, keeping and applying any
    validator declared for the replaced entry."""
    inject = getattr(catalog, "_inject", None)
    if inject is None:
        # A plain `catalog[name] = value` would silently drop validators.
        raise KedroSessionError(
            f"The catalog class '{type(catalog).__name__}' does not support "
            "runtime datasets because it does not implement `_inject()`."
        )
    for dataset_name, dataset_value in runtime_datasets.items():
        inject(dataset_name, dataset_value)
