"""This module provides ``kedro.abstract_config`` with the baseline
class model for a `ConfigLoader` implementation.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class AbstractConfigLoader(ABC):
    """``AbstractConfigLoader`` is the abstract base class
        for all `ConfigLoader` implementations.
    All user-defined `ConfigLoader` implementations should inherit
        from `AbstractConfigLoader` and implement all relevant abstract methods.
    """

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
        **kwargs  # pylint: disable=unused-argument
    ):
        self.conf_source = conf_source
        self.env = env
        self.runtime_params = runtime_params

    @abstractmethod  # pragma: no cover
    def get(self) -> Dict[str, Any]:
        """Required method to get all configurations."""
        pass


class BadConfigException(Exception):
    """Raised when a configuration file cannot be loaded, for instance
    due to wrong syntax or poor formatting.
    """

    pass


class MissingConfigException(Exception):
    """Raised when no configuration files can be found within a config path"""

    pass
