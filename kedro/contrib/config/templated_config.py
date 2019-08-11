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
or more configuration files from specified paths, and replace template strings with default values.
"""
import re
from typing import Any, Dict, List, Optional, Union

import jmespath

from kedro.config import ConfigLoader


class TemplatedConfigLoader(ConfigLoader):
    """
    Extension of the ConfigLoader class that allows for template values, wrapped in brackets like:
     ${..}, to be replaced by default values.

    Default values are provided in a dictionary.
    """

    def get(self, patterns: Union[str, List[str]], *,
            arg_values: Optional[Dict[str, Any]] = None):
        """
        Tries to resolve the template variables in the config dictionary provided by the
        ConfigLoader (super class) `get` method.

        Args:
            patterns: Glob patterns to match. Files, which names match
                any of the specified patterns, will be processed.
            arg_values: Optional dictionary containing default values.

        Returns:
            Dict[str, Any]:  A Python dictionary with the combined
                configuration from all configuration files. **Note:** any keys
                that start with `_` will be ignored.
                String values wrapped in `${..} will be replaced with default values if they can be
                found in the arg_values_dict).
        """

        if isinstance(patterns, str):
            patterns = [patterns]

        config_raw = super(TemplatedConfigLoader, self).get(*patterns)

        config_out = _replace_vals(config_raw, arg_values) if arg_values \
            else config_raw

        return config_out


def _replace_vals(val: Any, defaults: Dict[str, Any]) -> Any:
    """
    Recursive function that loops through the values of a map. In case another map or a list is
    encountered, it calls itsself. When a string is encountered it will use the default dict to
    replace strings that look like ${param_name} (where param_name can be any key value) with the
    corresponding value of the key 'param_name' in the default dict.

    Some notes on behavior:
        if val is not a dict, list or string, the same value gets passed back
        if val is a string and does not match the ${..} pattern, the same value gets passed back
        if the value inside ${..} does not match any keys in the dictionary, the same value gets
            passed back.
        if the ${..} is part of a larger string, the corresponding entry in the defaults dictionary
            gets parsed into a string and put into the larger string

    Examples:
        val = '${test_key}' with defaults = {'test_key': 'test_val'} returns 'test_val'
        val = 5 (i.e. not a dict, list or string) returns 5
        val = 'test_key' (i.e. does not match ${..} pattern returns 'test_key' (irrespective of
            defaults)
        val = '${wrong_test_key}' with defaults = {'test_key': 'test_val'} returns 'wrong_test_key'
        val = 'string-with-${test_key}' with defaults = {'test_key': 1000} returns
            'string-with-1000'

    Args:
        val: If this is a string of the format ${param_name}, it gets replaced by a parameter
        defaults: A lookup from string to string with replacement values

    Returns:
        either the replacement value, if input val is a string

    """

    if isinstance(val, dict):
        return {k: _replace_vals(val[k], defaults) for k in val.keys()}

    elif isinstance(val, list):
        return [_replace_vals(e, defaults) for e in val]

    elif isinstance(val, str):
        # Distinguish case where entire string matches, as the replacement can be different type
        pattern_full = r'^\$\{([^\}]*)\}$'
        match_full = re.search(pattern_full, val)
        if match_full:
            return jmespath.search(match_full.group(1), defaults) or val

        pattern_partial = r'\$\{([^\}]*)\}'
        return re.sub(pattern_partial,
                      lambda m: jmespath.search(m.group(1), defaults) or m.group(0),
                      val)
    return val

