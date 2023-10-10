"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files from specified paths, and format template strings
with the values from the passed dictionary.
"""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import jmespath

from kedro.config.abstract_config import AbstractConfigLoader
from kedro.config.common import _get_config_from_patterns, _remove_duplicates

IDENTIFIER_PATTERN = re.compile(
    r"""\$\{
    (?P<path>[A-Za-z0-9_\.]+)  # identifier
    (?:\|(?P<default>[^}]*))?  # optional default value
    \}""",
    re.VERBOSE,
)
FULL_STRING_IDENTIFIER_PATTERN = re.compile(
    r"^" + IDENTIFIER_PATTERN.pattern + r"$", re.VERBOSE
)


class TemplatedConfigLoader(AbstractConfigLoader):
    """
    Extension of the ``ConfigLoader`` class that allows for template values,
    wrapped in brackets like: ${...}, to be automatically formatted
    based on the configs.

    The easiest way to use this class is by setting the `CONFIG_LOADER_CLASS` constant
    in `settings.py`.

    Example:
    ::

        >>> # in settings.py
        >>> from kedro.config import TemplatedConfigLoader
        >>>
        >>> CONFIG_LOADER_CLASS = TemplatedConfigLoader
        >>> CONFIG_LOADER_ARGS = {
        >>>     "globals_pattern": "*globals.yml",
        >>> }

    The contents of the dictionary resulting from the `globals_pattern` get
    merged with the ``globals_dict``. In case of conflicts, the keys in
    ``globals_dict`` take precedence.
    If the formatting key is missing from the dictionary, the default template
    value is used (the format is "${key|default value}"). If no default is set,
    a ``ValueError`` will be raised.

    Global parameters can be namespaced as well. An example could work as follows:

    `globals.yml`
    ::

        bucket: "my_s3_bucket"

        environment: "dev"

        datasets:
            csv: "pandas.CSVDataset"
            spark: "spark.SparkDataset"

        folders:
            raw: "01_raw"
            int: "02_intermediate"
            pri: "03_primary"
            fea: "04_feature"


    `catalog.yml`
    ::

        raw_boat_data:
            type: "${datasets.spark}"
            filepath: "s3a://${bucket}/${environment}/${folders.raw}/boats.csv"
            file_format: parquet

        raw_car_data:
            type: "${datasets.csv}"
            filepath: "s3://${bucket}/data/${environment}/${folders.raw}/cars.csv"

    This uses ``jmespath`` in the background. For more information see:
    https://github.com/jmespath/jmespath.py and https://jmespath.org/.
    """

    def __init__(  # noqa: too-many-arguments
        self,
        conf_source: str,
        env: str = None,
        runtime_params: dict[str, Any] = None,
        config_patterns: dict[str, list[str]] = None,
        *,
        base_env: str = "base",
        default_run_env: str = "local",
        globals_pattern: str | None = None,
        globals_dict: dict[str, Any] | None = None,
    ):
        """Instantiates a ``TemplatedConfigLoader``.

        Args:
            conf_source: Path to use as root directory for loading configuration.
            env: Environment that will take precedence over base.
            runtime_params: Extra parameters passed to a Kedro run.
            config_patterns: Regex patterns that specify the naming convention for configuration
                files so they can be loaded. Can be customised by supplying config_patterns as
                in `CONFIG_LOADER_ARGS` in `settings.py`.
            base_env:
            default_run_env:
            globals_pattern: Optional keyword-only argument specifying a glob
                pattern. Files that match the pattern will be loaded as a
                formatting dictionary.
            globals_dict: Optional keyword-only argument specifying a formatting
                dictionary. This dictionary will get merged with the globals dictionary
                obtained from the globals_pattern. In case of duplicate keys, the
                ``globals_dict`` keys take precedence.
        """
        self.config_patterns = {
            "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
            "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
            "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
        }
        self.config_patterns.update(config_patterns or {})

        super().__init__(
            conf_source=conf_source, env=env, runtime_params=runtime_params
        )
        self.base_env = base_env
        self.default_run_env = default_run_env

        self._config_mapping = (
            _get_config_from_patterns(
                conf_paths=self.conf_paths,
                patterns=[globals_pattern],
                ac_template=False,
            )
            if globals_pattern
            else {}
        )
        globals_dict = deepcopy(globals_dict) or {}
        self._config_mapping = {**self._config_mapping, **globals_dict}

    def __getitem__(self, key):
        # Allow bypassing of loading config from patterns if a key and value have been set
        # explicitly on the ``TemplatedConfigLoader`` instance.
        if key in self:
            return super().__getitem__(key)
        return self.get(*self.config_patterns[key])

    def __repr__(self):  # pragma: no cover
        return (
            f"TemplatedConfigLoader(conf_source={self.conf_source}, env={self.env}, "
            f"config_patterns={self.config_patterns})"
        )

    @property
    def conf_paths(self):
        """Property method to return deduplicated configuration paths."""
        return _remove_duplicates(self._build_conf_paths())

    def get(self, *patterns: str) -> dict[str, Any]:  # type: ignore
        """Tries to resolve the template variables in the config dictionary
        provided by the ``ConfigLoader`` (super class) ``get`` method using the
        dictionary of replacement values obtained in the ``__init__`` method.

        Args:
            *patterns: Glob patterns to match. Files, which names match
                any of the specified patterns, will be processed.

        Returns:
            A Python dictionary with the combined configuration from all
            configuration files. **Note:** any keys that start with `_`
            will be ignored. String values wrapped in `${...}` will be
            replaced with the result of the corresponding JMESpath
            expression evaluated against globals.

        Raises:
            ValueError: malformed config found.
        """
        config_raw = _get_config_from_patterns(
            conf_paths=self.conf_paths, patterns=patterns, ac_template=True
        )
        return _format_object(config_raw, self._config_mapping)

    def _build_conf_paths(self) -> Iterable[str]:
        run_env = self.env or self.default_run_env
        return [
            str(Path(self.conf_source) / self.base_env),
            str(Path(self.conf_source) / run_env),
        ]


def _format_object(val: Any, format_dict: dict[str, Any]) -> Any:
    """Recursive function that loops through the values of a map. In case another
    map or a list is encountered, it calls itself. When a string is encountered,
    it will use the `format_dict` to replace strings that look like `${expr}`,
    where `expr` is a JMESPath expression evaluated against `format_dict`.

    Some notes on behavior:
        * If val is not a dict, list or string, the same value gets passed back.
        * If val is a string and does not match the ${...} pattern, the same
            value gets passed back.
        * If the value inside ${...} does not match any keys in the dictionary,
            the error is raised, unless a default is provided.
        * If the default is provided with ${...|default}, and the key is not
            found in the dictionary, the default value gets passed back.
        * If the ${...} is part of a larger string, the corresponding entry in
            the `format_dict` gets parsed into a string and put into the
            larger string.

    Examples:
        val = "${test_key}" with format_dict = {'test_key': 'test_val'} returns
            'test_val'
        val = 5 (i.e. not a dict, list or string) returns 5
        val = "test_key" (i.e. does not match ${...} pattern returns 'test_key'
            (irrespective of `format_dict`)
        val = "${wrong_test_key}" with format_dict = {'test_key': 'test_val'}
            raises ``ValueError``
        val = "string-with-${test_key}" with format_dict = {'test_key': 1000}
            returns "string-with-1000"
        val = "${wrong_test_key|default_value}" with format_dict = {}
            returns 'default_value'

    Args:
        val: If this is a string of the format `${expr}`, it gets replaced
            by the result of JMESPath expression
        format_dict: A lookup from string to string with replacement values

    Returns:
        A string formatted according to the ``format_dict`` input.

    Raises:
        ValueError: The input data is malformed.
    """

    def _format_string(match):
        value = jmespath.search(match.group("path"), format_dict)

        if value is None:
            if match.group("default") is None:
                raise ValueError(
                    f"Failed to format pattern '{match.group(0)}': "
                    f"no config value found, no default provided"
                )
            return match.group("default")

        return value

    if isinstance(val, dict):
        new_dict = {}

        for key, value in val.items():
            if isinstance(key, str):
                formatted_key = _format_object(key, format_dict)
                if not isinstance(formatted_key, str):
                    raise ValueError(
                        f"When formatting '{key}' key, only string values can be used. "
                        f"'{formatted_key}' found"
                    )

                key = formatted_key  # noqa: PLW2901

            new_dict[key] = _format_object(value, format_dict)

        return new_dict

    if isinstance(val, list):
        return [_format_object(e, format_dict) for e in val]

    if isinstance(val, str):
        # Distinguish case where entire string matches the pattern,
        # as the replacement can be of a different type
        match_full = FULL_STRING_IDENTIFIER_PATTERN.match(val)

        if match_full:
            return _format_string(match_full)

        return IDENTIFIER_PATTERN.sub(lambda m: str(_format_string(m)), val)
    return val
