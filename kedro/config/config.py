"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files from specified paths.
"""
from pathlib import Path
from typing import Any, Dict, Iterable

from kedro.config import AbstractConfigLoader
from kedro.config.common import _get_config_from_patterns, _remove_duplicates


class ConfigLoader(AbstractConfigLoader):
    """Recursively scan directories (config paths) contained in ``conf_source`` for
    configuration files with a ``yaml``, ``yml``, ``json``, ``ini``,
    ``pickle``, ``xml`` or ``properties`` extension, load them,
    and return them in the form of a config dictionary.

    The first processed config path is the ``base`` directory inside
    ``conf_source``. The optional ``env`` argument can be used to specify a
    subdirectory of ``conf_source`` to process as a config path after ``base``.

    When the same top-level key appears in any 2 config files located in
    the same (sub)directory, a ``ValueError`` is raised.

    When the same key appears in any 2 config files located in different
    (sub)directories, the last processed config path takes precedence
    and overrides this key.

    For example, if your ``conf_source`` looks like this:
    ::

        .
        `-- conf
            |-- README.md
            |-- base
            |   |-- catalog.yml
            |   |-- logging.yml
            |   `-- experiment1
            |       `-- parameters.yml
            `-- local
                |-- catalog.yml
                |-- db.ini
                |-- experiment1
                |   |-- parameters.yml
                |   `-- model_parameters.yml
                `-- experiment2
                    `-- parameters.yml


    You can access the different configurations as follows:
    ::

        >>> import logging.config
        >>> from kedro.config import ConfigLoader
        >>> from kedro.framework.project import settings
        >>>
        >>> conf_path = str(project_path / settings.CONF_SOURCE)
        >>> conf_loader = ConfigLoader(conf_source=conf_path, env="local")
        >>>
        >>> conf_logging = conf_loader.get('logging*')
        >>> logging.config.dictConfig(conf_logging)  # set logging conf
        >>>
        >>> conf_catalog = conf_loader.get('catalog*', 'catalog*/**')
        >>> conf_params = conf_loader.get('**/parameters.yml')

    """

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
        *,
        base_env: str = "base",
        default_run_env: str = "local",
    ):
        """Instantiates a ``ConfigLoader``.

        Args:
            conf_source: Path to use as root directory for loading configuration.
            env: Environment that will take precedence over base.
            runtime_params: Extra parameters passed to a Kedro run.
            base_env: Name of the base environment. Defaults to `"base"`.
                This is used in the `conf_paths` property method to construct
                the configuration paths.
            default_run_env: Name of the base environment. Defaults to `"local"`.
                This is used in the `conf_paths` property method to construct
                the configuration paths. Can be overriden by supplying the `env` argument.
        """
        super().__init__(
            conf_source=conf_source, env=env, runtime_params=runtime_params
        )
        self.base_env = base_env
        self.default_run_env = default_run_env

    @property
    def conf_paths(self):
        """Property method to return deduplicated configuration paths."""
        return _remove_duplicates(self._build_conf_paths())

    def get(self, *patterns: str) -> Dict[str, Any]:
        return _get_config_from_patterns(
            conf_paths=self.conf_paths, patterns=list(patterns)
        )

    def _build_conf_paths(self) -> Iterable[str]:
        run_env = self.env or self.default_run_env
        return [
            str(Path(self.conf_source) / self.base_env),
            str(Path(self.conf_source) / run_env),
        ]
