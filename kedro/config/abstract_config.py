"""This module provides ``kedro.abstract_config`` with the baseline
class model for a `ConfigLoader` implementation.
"""
from __future__ import annotations

from collections import UserDict
from typing import Any


class AbstractConfigLoader(UserDict):
    """``AbstractConfigLoader`` is the abstract base class
        for all `ConfigLoader` implementations.
    All user-defined `ConfigLoader` implementations should inherit
        from `AbstractConfigLoader` and implement all relevant abstract methods.
    """

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: dict[str, Any] = None,
        **kwargs,
    ):
        super().__init__()
        self.conf_source = conf_source
        self.env = env
        self.runtime_params = runtime_params or {}


class BadConfigException(Exception):
    """Raised when a configuration file cannot be loaded, for instance
    due to wrong syntax or poor formatting.
    """

    pass


class MissingConfigException(Exception):
    """Raised when no configuration files can be found within a config path"""

    pass
