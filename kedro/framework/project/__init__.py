"""``kedro.framework.project`` module provides utitlity to
configure a Kedro project and access its settings."""
# noqa: redefined-outer-name,unused-argument,global-statement
from __future__ import annotations

import importlib
import logging.config
import operator
import os
import traceback
import types
import warnings
from collections import UserDict
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import importlib_resources
import yaml
from dynaconf import LazySettings
from dynaconf.validator import ValidationError, Validator

from kedro.pipeline import Pipeline, pipeline

IMPORT_ERROR_MESSAGE = (
    "An error occurred while importing the '{module}' module. Nothing "
    "defined therein will be returned by 'find_pipelines'.\n\n{tb_exc}"
)


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
                    f"Invalid value '{setting_value.__module__}.{setting_value.__qualname__}' "
                    f"received for setting '{name}'. It must be a subclass of "
                    f"'{default_class.__module__}.{default_class.__qualname__}'."
                )


class _HasSharedParentClassValidator(Validator):
    """A validator to check that the parent of the default class is an ancestor of
    the settings value."""

    def validate(self, settings, *args, **kwargs):
        super().validate(settings, *args, **kwargs)

        default_class = self.default(settings, self)
        for name in self.names:
            setting_value = getattr(settings, name)
            # In the case of ConfigLoader, default_class.mro() will be:
            # [kedro.config.config.ConfigLoader,
            # kedro.config.abstract_config.AbstractConfigLoader,
            # abc.ABC,
            # object]
            # We pick out the direct parent and check if it's in any of the ancestors of
            # the supplied setting_value. This assumes that the direct parent is
            # the abstract class that must be inherited from.
            # A more general check just for a shared ancestor would be:
            # set(default_class.mro()) & set(setting_value.mro()) - {abc.ABC, object}
            default_class_parent = default_class.mro()[1]
            if default_class_parent not in setting_value.mro():
                raise ValidationError(
                    f"Invalid value '{setting_value.__module__}.{setting_value.__qualname__}' "
                    f"received for setting '{name}'. It must be a subclass of "
                    f"'{default_class_parent.__module__}.{default_class_parent.__qualname__}'."
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
    _CONFIG_LOADER_CLASS = _HasSharedParentClassValidator(
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

    # noqa: protected-access
    def inner(self, *args, **kwargs):
        self._load_data()
        return func(self._content, *args, **kwargs)

    return inner


class _ProjectPipelines(MutableMapping):
    """A read-only lazy dictionary-like object to hold the project pipelines.
    When configured, it stores the pipelines module.
    On first data access, e.g. through __getitem__, it will load the registered pipelines

    This object is initialized lazily for a few reasons:

    1. To support an unified way of importing via `from kedro.framework.project import pipelines`.
       The pipelines object is initializedlazily since the framework doesn't have knowledge about
       the project until `bootstrap_project` is run.
    2. To speed up Kedro CLI performance. Loading the pipelines incurs overhead, as all related
       modules need to be imported.
    3. To ensure Kedro CLI remains functional when pipelines are broken. During development, broken
       pipelines are common, but they shouldn't prevent other parts of Kedro CLI from functioning
       properly (e.g. `kedro -h`).
    """

    def __init__(self) -> None:
        self._pipelines_module: str | None = None
        self._is_data_loaded = False
        self._content: dict[str, Pipeline] = {}

    @staticmethod
    def _get_pipelines_registry_callable(pipelines_module: str):
        module_obj = importlib.import_module(pipelines_module)
        register_pipelines = getattr(module_obj, "register_pipelines")
        return register_pipelines

    def _load_data(self):
        """Lazily read pipelines defined in the pipelines registry module."""

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

    def configure(self, pipelines_module: str | None = None) -> None:
        """Configure the pipelines_module to load the pipelines dictionary.
        Reset the data loading state so that after every ``configure`` call,
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
    keys = _load_data_wrapper(operator.methodcaller("keys"))
    values = _load_data_wrapper(operator.methodcaller("values"))
    items = _load_data_wrapper(operator.methodcaller("items"))

    # Presentation methods
    __repr__ = _load_data_wrapper(repr)
    __str__ = _load_data_wrapper(str)


class _ProjectLogging(UserDict):
    # noqa: super-init-not-called
    def __init__(self):
        """Initialise project logging. The path to logging configuration is given in
        environment variable KEDRO_LOGGING_CONFIG (defaults to default_logging.yml)."""
        path = os.environ.get(
            "KEDRO_LOGGING_CONFIG", Path(__file__).parent / "default_logging.yml"
        )
        logging_config = Path(path).read_text(encoding="utf-8")
        self.configure(yaml.safe_load(logging_config))

    def configure(self, logging_config: dict[str, Any]) -> None:
        """Configure project logging using ``logging_config`` (e.g. from project
        logging.yml). We store this in the UserDict data so that it can be reconfigured
        in _bootstrap_subprocess.
        """
        logging.config.dictConfig(logging_config)
        self.data = logging_config

    def set_project_logging(self, package_name: str):
        """Add the project level logging to the loggers upon provision of a package name.
        Checks if project logger already exists to prevent overwriting, if none exists
        it defaults to setting project logs at INFO level."""
        if package_name not in self.data["loggers"]:
            self.data["loggers"][package_name] = {"level": "INFO"}
            self.configure(self.data)


PACKAGE_NAME = None
LOGGING = _ProjectLogging()

settings = _ProjectSettings()

pipelines = _ProjectPipelines()


def configure_project(package_name: str):
    """Configure a Kedro project by populating its settings with values
    defined in user's settings.py and pipeline_registry.py.
    """
    settings_module = f"{package_name}.settings"
    settings.configure(settings_module)

    pipelines_module = f"{package_name}.pipeline_registry"
    pipelines.configure(pipelines_module)

    # Once the project is successfully configured once, store PACKAGE_NAME as a
    # global variable to make it easily accessible. This is used by validate_settings()
    # below, and also by ParallelRunner on Windows, as package_name is required every
    # time a new subprocess is spawned.
    global PACKAGE_NAME  # noqa: PLW0603
    PACKAGE_NAME = package_name

    if PACKAGE_NAME:
        LOGGING.set_project_logging(PACKAGE_NAME)


def configure_logging(logging_config: dict[str, Any]) -> None:
    """Configure logging according to ``logging_config`` dictionary."""
    LOGGING.configure(logging_config)


def validate_settings():
    """Eagerly validate that the settings module is importable if it exists. This is desirable to
    surface any syntax or import errors early. In particular, without eagerly importing
    the settings module, dynaconf would silence any import error (e.g. missing
    dependency, missing/mislabelled pipeline), and users would instead get a cryptic
    error message ``Expected an instance of `ConfigLoader`, got `NoneType` instead``.
    More info on the dynaconf issue: https://github.com/rochacbruno/dynaconf/issues/460
    """
    if PACKAGE_NAME is None:
        raise ValueError(
            "Package name not found. Make sure you have configured the project using "
            "'bootstrap_project'. This should happen automatically if you are using "
            "Kedro command line interface."
        )
    # Check if file exists, if it does, validate it.
    if importlib.util.find_spec(f"{PACKAGE_NAME}.settings") is not None:  # type: ignore
        importlib.import_module(f"{PACKAGE_NAME}.settings")
    else:
        logger = logging.getLogger(__name__)
        logger.warning("No 'settings.py' found, defaults will be used.")


def _create_pipeline(pipeline_module: types.ModuleType) -> Pipeline | None:
    if not hasattr(pipeline_module, "create_pipeline"):
        warnings.warn(
            f"The '{pipeline_module.__name__}' module does not "
            f"expose a 'create_pipeline' function, so no pipelines "
            f"defined therein will be returned by 'find_pipelines'."
        )
        return None

    obj = getattr(pipeline_module, "create_pipeline")()
    if not isinstance(obj, Pipeline):
        warnings.warn(
            f"Expected the 'create_pipeline' function in the "
            f"'{pipeline_module.__name__}' module to return a "
            f"'Pipeline' object, got '{type(obj).__name__}' "
            f"instead. Nothing defined therein will be returned by "
            f"'find_pipelines'."
        )
        return None

    return obj


def find_pipelines() -> dict[str, Pipeline]:  # noqa: PLR0912
    """Automatically find modular pipelines having a ``create_pipeline``
    function. By default, projects created using Kedro 0.18.3 and higher
    call this function to autoregister pipelines upon creation/addition.

    Projects that require more fine-grained control can still define the
    pipeline registry without calling this function. Alternatively, they
    can modify the mapping generated by the ``find_pipelines`` function.

    For more information on the pipeline registry and autodiscovery, see
    https://kedro.readthedocs.io/en/latest/nodes_and_pipelines/pipeline_registry.html

    Returns:
        A generated mapping from pipeline names to ``Pipeline`` objects.

    Warns:
        UserWarning: When a module does not expose a ``create_pipeline``
            function, the ``create_pipeline`` function does not return a
            ``Pipeline`` object, or if the module import fails up front.
    """
    pipeline_obj = None

    # Handle the simplified project structure found in several starters.
    pipeline_module_name = f"{PACKAGE_NAME}.pipeline"
    try:
        pipeline_module = importlib.import_module(pipeline_module_name)
    except Exception as exc:  # noqa: broad-except
        if str(exc) != f"No module named '{pipeline_module_name}'":
            warnings.warn(
                IMPORT_ERROR_MESSAGE.format(
                    module=pipeline_module_name, tb_exc=traceback.format_exc()
                )
            )
    else:
        pipeline_obj = _create_pipeline(pipeline_module)

    pipelines_dict = {"__default__": pipeline_obj or pipeline([])}

    # Handle the case that a project doesn't have a pipelines directory.
    try:
        pipelines_package = importlib_resources.files(f"{PACKAGE_NAME}.pipelines")
    except ModuleNotFoundError as exc:
        if str(exc) == f"No module named '{PACKAGE_NAME}.pipelines'":
            return pipelines_dict

    for pipeline_dir in pipelines_package.iterdir():
        if not pipeline_dir.is_dir():
            continue

        pipeline_name = pipeline_dir.name
        if pipeline_name == "__pycache__":
            continue
        # Prevent imports of hidden directories/files
        if pipeline_name.startswith("."):
            continue

        pipeline_module_name = f"{PACKAGE_NAME}.pipelines.{pipeline_name}"
        try:
            pipeline_module = importlib.import_module(pipeline_module_name)
        except:  # noqa: bare-except  # noqa: E722
            warnings.warn(
                IMPORT_ERROR_MESSAGE.format(
                    module=pipeline_module_name, tb_exc=traceback.format_exc()
                )
            )
            continue

        pipeline_obj = _create_pipeline(pipeline_module)
        if pipeline_obj is not None:
            pipelines_dict[pipeline_name] = pipeline_obj
    return pipelines_dict
