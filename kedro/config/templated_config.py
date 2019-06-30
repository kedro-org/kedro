"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files from specified paths, and replace template strings with default values.
"""
import re
from typing import Any, Dict, List, Optional, Union

from kedro.config import ConfigLoader


class TemplatedConfigLoader(ConfigLoader):
    """
    Extension of the ConfigLoader class that allows for template values, wrapped in brackets like:
     ${..}, to be replaced by default values.

    Default values are either provided by a values.yml file in the specified conf_paths directories,
    or in a dictionary. User has the option to not search directory for values.yml when a dictionary
    has been provided, using the search_for_values flag. Otherwise these two will be merged, where
    the provided dictionary takes precedence over the values.yml file.
    """

    def resolve(self, patterns: Union[str, List[str]],
                arg_values_dict: Optional[Dict[str, Any]] = None, search_for_values: bool = True):
        """
        Tries to resolve the template variables in the config dictionary provided by the
        ConfigLoader (super class) `get` method.

        Args:
            patterns: Glob patterns to match. Files, which names match
                any of the specified patterns, will be processed.
            arg_values_dict: Optional dictionary containing default values.
            search_for_values: Boolean indicating whether the user wants to search the conf_paths
            directories for default values or not.

        Raises:
            ValueError: If no values dict is provided and search_for_values is set to False.

        Returns:
            Dict[str, Any]:  A Python dictionary with the combined
                configuration from all configuration files. **Note:** any keys
                that start with `_` will be ignored.
                String values wrapped in `${..} will be replaced with default values if they can be
                found in one of the provided default values locations (values.yml or default_values
                dict).
        """

        if isinstance(patterns, str):
            patterns = [patterns]

        config_raw = self.get(*patterns)

        if not search_for_values and not arg_values_dict:
            raise ValueError(
                'Must specify values_dict when search_for_values is set to false.'
            )

        file_values_dict = self.get("*values.yml") if search_for_values else None

        combined_values_dict = \
            {**file_values_dict, **arg_values_dict} if arg_values_dict and file_values_dict \
            else arg_values_dict or file_values_dict

        return _replace_vals_map(config_raw, combined_values_dict)


def _replace_val(val: Any, defaults: Dict[str, str]) -> Any:
    """
    Use the default dict to replace strings that look like ${param_name} (where param_name can be
    any key value) with the corresponding value of the key 'param_name' in the default dict.

    Some notes on behavior:
        if val is not a string, the same value gets passed back
        if val does not match the ${..} pattern, the same value gets passed back
        if the value inside ${..} does not match any keys in the dictionary, the same value gets
        passed back.

    Examples:
        val = '${test_key}' with defaults = {'test_key': 'test_val'} returns 'test_val'
        val = ['string1', 'string2'] (i.e. a list of strings) returns ['string1', 'string2']
            (irrespective of defaults)
        val = 'test_key' (i.e. does not match ${..} pattern returns 'test_key' (irrespective of
            defaults)
        val = '${wrong_test_key}' with defaults = {'test_key': 'test_val'} returns 'wrong_test_key'

    Args:
        val: If this is a string of the format ${param_name}, it gets replaced by a parameter
        defaults: A lookup from string to string with replacement values

    Returns:
        either the replacement value, if input val is a string

    """
    return re.sub(r'\$\{([^\}]*)\}', lambda m: defaults.get(m.group(1), m.group(0)),
                  val) if isinstance(val, str) \
        else val


def _replace_vals_list(listt: List[Any], defaults: Dict[str, str]) -> List[Any]:
    """
    Loops through list and applies _replace_vals function
    Args:
        listt: List containing any value
        defaults: default value dictionary to be applied to each element (according to rules
        described in _replace_vals docstring

    Returns:
        List with string values replaced if they match the rules described in _replace_vals
        docstring

    """
    return [_replace_val(e, defaults) for e in listt]


def _replace_vals_map(mapp: Dict[str, Any], defaults: Dict[str, str]) -> Dict[str, Any]:
    """
    Recursive function that loops through the values of a map. In case another map is encountered,
    it calls itsself, otherwise it calls either _replace_vals_list or _replace_val, depending on
    data type of the value.
    Args:
        mapp: A map from string to any. In the context of the ConfigLoader class, this would be a
        config dictionary,
            obtained from a yml file.
        defaults: A mapping from string to string (right now no support for replacement with maps or
        lists).

    Returns:
        a map with parameters replaced with values.

    """
    return {k: _replace_vals_map(mapp[k], defaults) if isinstance(mapp[k], dict)
            else _replace_vals_list(mapp[k], defaults) if isinstance(mapp[k], list)
            else _replace_val(mapp[k], defaults) for k in mapp.keys()}
