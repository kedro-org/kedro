# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files from specified paths.
"""
import logging
import re
from glob import iglob
from pathlib import Path
from typing import AbstractSet, Any, Dict, List, Mapping, Tuple, Union

import anyconfig

SUPPORTED_EXTENSIONS = [
    ".yml",
    ".yaml",
    ".json",
    ".ini",
    ".pickle",
    ".properties",
    ".xml",
    ".shellvars",
]


class MissingConfigException(Exception):
    """Raised when no configuration files can be found within a config path"""

    pass


class ConfigLoader:
    """Recursively scan the directories specified in ``conf_paths`` for
        configuration files with a ``yaml``, ``yml``, ``json``, ``ini``,
        ``pickle``, ``xml``, ``properties`` or ``shellvars`` extension,
        load them, and return them in the form of a config dictionary.

        When the same top-level key appears in any 2 config files located in
        the same ``conf_path`` (sub)directory, a ``ValueError`` is raised.

        When the same key appears in any 2 config files located in different
        ``conf_path`` directories, the last processed config path takes
        precedence and overrides this key.

        For example, if your ``conf_path`` looks like this:
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
            >>>
            >>> conf_paths = ['conf/base', 'conf/local']
            >>> conf_loader = ConfigLoader(conf_paths)
            >>>
            >>> conf_logging = conf_loader.get('logging*')
            >>> logging.config.dictConfig(conf_logging)  # set logging conf
            >>>
            >>> conf_catalog = conf_loader.get('catalog*', 'catalog*/**')
            >>> conf_params = conf_loader.get('**/parameters.yml')

    """

    def __init__(self, conf_paths: Union[str, List[str]]):
        """Instantiate a ConfigLoader.

        Args:
            conf_paths: Non-empty path or list of paths to configuration
                directories.
        Raises:
            ValueError: If ``conf_paths`` is empty.

        """
        if not conf_paths:
            raise ValueError(
                "`conf_paths` must contain at least one path to "
                "load configuration files from."
            )
        if isinstance(conf_paths, str):
            conf_paths = [conf_paths]
        self.conf_paths = conf_paths
        self.logger = logging.getLogger(__name__)

    def get(self, *patterns: Tuple[str]) -> Dict[str, Any]:
        """Recursively scan for configuration files, load and merge them, and
        return them in the form of a config dictionary.

        Args:
            patterns: Glob patterns to match. Files, which names match
                any of the specified patterns, will be processed.

        Raises:
            ValueError: If 2 or more configuration files inside the same
                config path (or its subdirectories) contain the same
                top-level key.
            MissingConfigException: If no configuration files exist within
                a specified config path.

        Returns:
            Dict[str, Any]:  A Python dictionary with the combined
                configuration from all configuration files. **Note:** any keys
                that start with `_` will be ignored.
        """

        if not patterns:
            raise ValueError(
                "`patterns` must contain at least one glob "
                "pattern to match config filenames against."
            )

        config = {}  # type: Dict[str, Any]
        processed_files = []

        for conf_path in self.conf_paths:
            new_conf, new_processed_files = _load_config(conf_path, list(patterns))
            common_keys = config.keys() & new_conf.keys()
            if common_keys:
                sorted_keys = ", ".join(sorted(common_keys))
                msg = (
                    "Config from path `%s` will override the following "
                    "existing top-level config keys: %s"
                )
                self.logger.debug(msg, conf_path, sorted_keys)
            config.update(new_conf)
            processed_files.extend(new_processed_files)
        if not processed_files:
            raise MissingConfigException(
                "No files found in {} matching the glob "
                "pattern(s): {}".format(str(self.conf_paths), str(list(patterns)))
            )

        params = config.pop('templates', {})

        return _replace_vals_map(config, params)


def _load_config(
    conf_path: str, patterns: List[str]
) -> Tuple[Dict[str, Any], List[Path]]:
    """Recursively load all configuration files, which satisfy
    a given list of glob patterns from a specific path.

    Args:
        conf_path: Path to a kedro configuration directory.
        patterns: List of glob patterns to match the filenames against.

    Raises:
        ValueError: If 2 or more configuration files contain the same key(s).

    Returns:
        Resulting configuration dictionary.

    """

    conf_path = Path(conf_path)
    if not conf_path.is_dir():
        raise ValueError(
            "Given configuration path either does not exist "
            "or is not a valid directory: {0}".format(conf_path)
        )
    config = {}
    keys_by_filepath = {}  # type: Dict[Path, AbstractSet[str]]

    def _check_dups(file1, conf):
        dups = []
        for file2, keys in keys_by_filepath.items():
            common = ", ".join(sorted(conf.keys() & keys))
            if common:
                if len(common) > 100:
                    common = common[:100] + "..."
                dups.append(str(file2) + ": " + common)

        if dups:
            msg = "Duplicate keys found in {0} and:\n- {1}".format(
                file1, "\n- ".join(dups)
            )
            raise ValueError(msg)

    for path in _path_lookup(conf_path, patterns):
        cfg = {k: v for k, v in anyconfig.load(path).items() if not k.startswith("_")}
        _check_dups(path, cfg)
        keys_by_filepath[path] = cfg.keys()
        config.update(cfg)
    return config, list(keys_by_filepath.keys())


def _path_lookup(conf_path: Path, patterns: List[str]) -> List[Path]:
    """Return a sorted list of all configuration files from ``conf_path`` or
    its subdirectories, which satisfy a given list of glob patterns.

    Args:
        conf_path: Path to configuration directory.
        patterns: List of glob patterns to match the filenames against.

    Returns:
        Sorted list of ``Path`` objects representing configuration files.

    """
    result = set()

    for pattern in patterns:
        for path in conf_path.resolve().glob(pattern):
            if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
                result.add(path)
    return sorted(result)


def _replace_val(val: Any, defaults: Mapping[str, str]) -> Any:
    """
    Use the default dict to replace strings that look like ${param_name} (where param_name can be any key value) with
    the corresponding value of the key 'param_name' in the default dict.

    Some notes on behavior:
        if val is not a string, the same value gets passed back
        if val does not match the ${..} pattern, the same value gets passed back
        if the value inside ${..} does not match any keys in the dictionary, the same value gets passed back.

    Examples:
        val = '${test_key}' with defaults = {'test_key': 'test_val'} returns 'test_val'
        val = ['string1', 'string2'] (i.e. a list of strings) returns ['string1', 'string2'] (irrespective of defaults)
        val = 'test_key' (i.e. does not match ${..} pattern returns 'test_key' (irrespective of defaults)
        val = '${wrong_test_key}' with defaults = {'test_key': 'test_val'} returns 'wrong_test_key'

    Args:
        val: If this is a string of the format ${param_name}, it gets replaced by a parameter
        defaults: A lookup from string to string with replacement values

    Returns:
        either the replacement value, if input val is a string

    """
    return re.sub(r'\$\{([^\}]*)\}', lambda m: defaults.get(m.group(1), m.group(0)), val) if isinstance(val, str) \
        else val


def _replace_vals_list(listt: List[Any], defaults: Mapping[str, str]) -> List[Any]:
    """
    Loops through list and applies _replace_vals function
    Args:
        listt: List containing any value
        defaults: default value dictionary to be applied to each element (according to rules described in _replace_vals
            docstring

    Returns:
        List with string values replaced if they match the rules described in _replace_vals docstring

    """
    return [_replace_val(e, defaults) for e in listt]


def _replace_vals_map(mapp: Mapping[str, Any], defaults: Mapping[str, str]) -> Mapping[str, Any]:
    """
    Recursive function that loops through the values of a map. In case another map is encountered, it calls itsself,
    otherwise it calls either _replace_vals_list or _replace_val, depending on data type of the value.
    Args:
        mapp: A map from string to any. In the context of the ConfigLoader class, this would be a config dictionary,
            obtained from a yml file.
        defaults: A mapping from string to string (right now no support for replacement with maps or lists).

    Returns:
        a map with parameters replaced with values.

    """
    return {k: _replace_vals_map(mapp[k], defaults) if isinstance(mapp[k], dict)
            else _replace_vals_list(mapp[k], defaults) if isinstance(mapp[k], list)
            else _replace_val(mapp[k], defaults) for k in mapp.keys()}
