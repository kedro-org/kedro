"""``kedro.framework.project`` module provides utitlity to
configure a Kedro project and access its settings."""
# pylint: disable=redefined-outer-name,unused-argument,global-statement
import logging

import sys

import inspect

import importlib
import logging.config
import operator
from collections.abc import MutableMapping
from typing import Any, Dict, Optional, Callable, List

from dynaconf import LazySettings
from dynaconf.validator import ValidationError, Validator

from kedro.pipeline import Pipeline


def _get_default_class(class_import_path):
    module, _, class_name = class_import_path.rpartition(".")

    def validator_func(settings, validators):
        return getattr(importlib.import_module(module), class_name)

    return validator_func


class _IsSubclassValidator(Validator):
    """A validator to check if the supplied setting value is a subclass of the default class"""

    def validate(self, settings, *args, **kwargs):
        super().validate(settings, *args, **kwargs)

        default_class = self.default(settings, self)
        for name in self.names:
            setting_value = getattr(settings, name)
            if not issubclass(setting_value, default_class):
                raise ValidationError(
                    f"Invalid value `{setting_value.__module__}.{setting_value.__qualname__}` "
                    f"received for setting `{name}`. It must be a subclass of "
                    f"`{default_class.__module__}.{default_class.__qualname__}`."
                )


class _ProjectSettings(LazySettings):
    """Define all settings available for users to configure in Kedro,
    along with their validation rules and default values.
    Use Dynaconf's LazySettings as base.
    """

    _CONF_SOURCE = Validator("CONF_SOURCE", default="conf")
    _HOOKS = Validator("HOOKS", default=tuple())
    _CONTEXT_CLASS = _IsSubclassValidator(
        "CONTEXT_CLASS",
        default=_get_default_class("kedro.framework.context.KedroContext"),
    )
    _SESSION_STORE_CLASS = _IsSubclassValidator(
        "SESSION_STORE_CLASS",
        default=_get_default_class("kedro.framework.session.session.BaseSessionStore"),
    )
    _SESSION_STORE_ARGS = Validator("SESSION_STORE_ARGS", default={})
    _DISABLE_HOOKS_FOR_PLUGINS = Validator("DISABLE_HOOKS_FOR_PLUGINS", default=tuple())
    _CONFIG_LOADER_CLASS = _IsSubclassValidator(
        "CONFIG_LOADER_CLASS", default=_get_default_class("kedro.config.ConfigLoader")
    )
    _CONFIG_LOADER_ARGS = Validator("CONFIG_LOADER_ARGS", default={})
    _DATA_CATALOG_CLASS = _IsSubclassValidator(
        "DATA_CATALOG_CLASS", default=_get_default_class("kedro.io.DataCatalog")
    )

    def __init__(self, *args, **kwargs):

        kwargs.update(
            validators=[
                self._CONF_SOURCE,
                self._HOOKS,
                self._CONTEXT_CLASS,
                self._SESSION_STORE_CLASS,
                self._SESSION_STORE_ARGS,
                self._DISABLE_HOOKS_FOR_PLUGINS,
                self._CONFIG_LOADER_CLASS,
                self._CONFIG_LOADER_ARGS,
                self._DATA_CATALOG_CLASS,
            ]
        )
        super().__init__(*args, **kwargs)


def _load_data_wrapper(func):
    """Wrap a method in _ProjectPipelines so that data is loaded on first access.
    Taking inspiration from dynaconf.utils.functional.new_method_proxy
    """
    # pylint: disable=protected-access
    def inner(self, *args, **kwargs):
        self._load_data()
        return func(self._content, *args, **kwargs)

    return inner


def _load_callable_wrapper(func):
    """Wrap a method in _ProjectPipelines so that data is loaded on first access.
    Taking inspiration from dynaconf.utils.functional.new_method_proxy
    """
    # pylint: disable=protected-access
    def inner(self, *args, **kwargs):
        self._load_callable()
        return func(self, *args, **kwargs)

    return inner


class _ProjectPipelines(MutableMapping):
    """A read-only lazy dictionary-like object to hold the project pipelines.
    On configure it will store the pipelines module.
    On first data access, e.g. through __getitem__, it will load the registered pipelines.
    """

    def __init__(self) -> None:
        self._pipelines_module: Optional[str] = None
        self._is_data_loaded = False
        self._content: Dict[str, Pipeline] = {}

    @staticmethod
    def _get_pipelines_registry_callable(pipelines_module: str):
        module_obj = importlib.import_module(pipelines_module)
        register_pipelines = getattr(module_obj, "register_pipelines")
        return register_pipelines

    def _load_data(self):
        """Lazily read pipelines defined in the pipelines registry module"""

        # If the pipelines dictionary has not been configured with a pipelines module
        # or if data has been loaded
        if self._pipelines_module is None or self._is_data_loaded:
            return

        register_pipelines = self._get_pipelines_registry_callable(
            self._pipelines_module
        )
        project_pipelines = register_pipelines()

        self._content = project_pipelines
        self._is_data_loaded = True

    def configure(self, pipelines_module: Optional[str] = None) -> None:
        """Configure the pipelines_module to load the pipelines dictionary.
        Reset the data loading state so that after every `configure` call,
        data are reloaded.
        """
        self._pipelines_module = pipelines_module
        self._is_data_loaded = False
        self._content = {}

    # Dict-like interface
    __getitem__ = _load_data_wrapper(operator.getitem)
    __setitem__ = _load_data_wrapper(operator.setitem)
    __delitem__ = _load_data_wrapper(operator.delitem)
    __iter__ = _load_data_wrapper(iter)
    __len__ = _load_data_wrapper(len)

    # Presentation methods
    __repr__ = _load_data_wrapper(repr)
    __str__ = _load_data_wrapper(str)


class _Run(Callable):
    def __init__(self) -> None:
        self._cli_module: Optional[str] = None
        self._is_callable_loaded = False
        self._callable: Optional[Callable] = None

    @staticmethod
    def _get_run_callable(cli_module: str):
        from kedro.framework.cli.utils import (
            KedroCliError,
            load_entry_points,
        )  ### needs to go in here to avoid circular imports

        def _find_run_command_in_plugins(plugins):
            for group in plugins:
                if "run" in group.commands:
                    return group.commands["run"]

        try:
            project_cli = importlib.import_module(cli_module)
            # fail gracefully if cli.py does not exist
        except ModuleNotFoundError as exc:
            if cli_module not in str(exc):
                raise
            plugins = load_entry_points("project")
            run = _find_run_command_in_plugins(plugins) if plugins else None
            if run:
                # use run command from installed plugin if it exists
                return run
            # use run command from the framework project
            from kedro.framework.cli.project import run

            return run
        # fail badly if cli.py exists, but has no `cli` in it
        if not hasattr(project_cli, "cli"):
            raise KedroCliError(f"Cannot load commands from {cli_module}")
        return project_cli.run

    def _load_callable(self):
        if self._cli_module is None or self._is_callable_loaded:
            return

        self._callable = self._get_run_callable(self._cli_module)
        self._is_callable_loaded = True

        self.__signature__ = inspect.signature(self._callable.callback)
        self.__annotations__ = self._callable.callback.__annotations__
        with self._callable.make_context("run", []) as ctx:
            self.__doc__ = self._callable.get_help(ctx)

    def configure(self, cli_module: Optional[str] = None) -> None:
        self._cli_module = cli_module
        self._is_callable_loaded = False
        self._callable = None
        # NEED ALL THREE OF THESE??

    @_load_callable_wrapper
    def __call__(self, args: Optional[List[str]] = None, **kwargs):
        # This is what happens under the hood of click. The click context contains
        # a list of arguments (e.g. ["--pipeline", "ds"]) and default values of
        # arguments that are not supplied. We forward the context to the
        # invocation of run. Any **kwargs supplied (e.g. `pipeline="ds"` will
        # overwrite the arguments supplied by the context. Overall this means
        # that an instantiation of _Run can handle both arguments from the CLI
        # (when invoked from a packaged project through the main entry point) and
        # using a Python API.
        # NOTE args rather than *args. So do run(["-p", "ds"]), not run("-p", "ds").
        # TRY ON DATABRICKS entrypoints
        args = args or []
        logging.info(args)
        logging.info(kwargs)
        with self._callable.make_context("run", args) as ctx:
            return ctx.forward(self._callable, **kwargs)

    # Presentation methods
    __repr__ = _load_callable_wrapper(repr)
    __str__ = _load_callable_wrapper(str)
    __doc__ = _load_callable_wrapper(__doc__)


#
# class _Run:
#     def __init__(self):
#         pass
#
#     # self._pipelines_module: Optional[str] = None
#     # self._is_data_loaded = False
#     # self._content: Dict[str, Pipeline] = {}
#
#     def _find_run_command(self):
#         from kedro.framework.cli.utils import (
#             KedroCliError,
#             load_entry_points,
#         )  ### needs to go in here to avoid circular imports
#
#         try:
#             project_cli = importlib.import_module(self._cli_module)
#             # fail gracefully if cli.py does not exist
#         except ModuleNotFoundError as exc:
#             if self._cli_module not in str(exc):
#                 raise
#             plugins = load_entry_points("project")
#             run = self._find_run_command_in_plugins(plugins) if plugins else None
#             if run:
#                 # use run command from installed plugin if it exists
#                 return run
#             # use run command from the framework project
#             from kedro.framework.cli.project import run
#
#             return run
#         # fail badly if cli.py exists, but has no `cli` in it
#         if not hasattr(project_cli, "cli"):
#             raise KedroCliError(f"Cannot load commands from {self._cli_module}")
#         return project_cli.run
#
#     @staticmethod
#     def _find_run_command_in_plugins(plugins):
#         for group in plugins:
#             if "run" in group.commands:
#                 return group.commands["run"]
#
#     def configure(self, cli_module: str):
#         self._cli_module = cli_module
#         self._run_cmd = self._find_run_command()
#
#         self.__call__.__func__.__name__ = self._run_cmd.callback.__name__
#         self.__call__.__func__.__signature__ = inspect.signature(self._run_cmd.callback)
#         self.__call__.__func__.__annotations__ = self._run_cmd.callback.__annotations__
#
#     def __call__(self, *args, **kwargs):
#         # This is what happens under the hood of click. The click context contains
#         # a list of arguments (e.g. ["--pipeline", "ds"]) and default values of
#         # arguments that are not supplied. We forward the context to the
#         # invocation of run. Any **kwargs supplied (e.g. `pipeline="ds"` will
#         # overwrite the arguments supplied by the context. Overall this means
#         # that an instantiation of _Run can handle both arguments from the CLI
#         # (when invoked from a packaged project through the main entry point) and
#         # using a Python API.
#         args = list(args) or sys.argv[1:]
#         with self._run_cmd.make_context("run", args) as ctx:
#             return ctx.forward(self._run_cmd, **kwargs)


PACKAGE_NAME = None
LOGGING = None

settings = _ProjectSettings()

pipelines = _ProjectPipelines()

run = _Run()


def configure_project(package_name: str):
    """Configure a Kedro project by populating its settings with values
    defined in user's settings.py and pipeline_registry.py.
    """
    settings_module = f"{package_name}.settings"
    settings.configure(settings_module)

    pipelines_module = f"{package_name}.pipeline_registry"
    pipelines.configure(pipelines_module)

    cli_module = f"{package_name}.cli"
    run.configure(cli_module)

    # Once the project is successfully configured once, store PACKAGE_NAME as a
    # global variable to make it easily accessible. This is used by validate_settings()
    # below, and also by ParallelRunner on Windows, as package_name is required every
    # time a new subprocess is spawned.
    global PACKAGE_NAME
    PACKAGE_NAME = package_name


def configure_logging(logging_config: Dict[str, Any]) -> None:
    """Configure logging to make it available as a global variable."""
    logging.config.dictConfig(logging_config)
    global LOGGING
    LOGGING = logging_config


def validate_settings():
    """Eagerly validate that the settings module is importable. This is desirable to
    surface any syntax or import errors early. In particular, without eagerly importing
    the settings module, dynaconf would silence any import error (e.g. missing
    dependency, missing/mislabelled pipeline), and users would instead get a cryptic
    error message ``Expected an instance of `ConfigLoader`, got `NoneType` instead``.
    More info on the dynaconf issue: https://github.com/rochacbruno/dynaconf/issues/460
    """
    importlib.import_module(f"{PACKAGE_NAME}.settings")
