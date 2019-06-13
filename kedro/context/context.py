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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module provides context for Kedro project."""

import importlib
import os
import sys
from pathlib import Path
from typing import Dict, Union

_LOADED_PATH = None


class KedroContextError(Exception):
    """Error occurred when loading project context."""


def load_context(proj_path: Union[str, Path]) -> Dict:
    """Load a context dictionary defined in `kedro_cli.__kedro_context__`.

    Args:
        proj_path: Path to the Kedro project.

    Returns:
        Kedro context dictionary.

    Raises:
        KedroContextError: If another project context has already been loaded.

    """
    # global due to importlib caching import_module("kedro_cli") call
    global _LOADED_PATH  # pylint: disable=global-statement

    proj_path = Path(proj_path).expanduser().resolve()

    if _LOADED_PATH and proj_path != _LOADED_PATH:
        raise KedroContextError(
            "Cannot load context for `{}`, since another project `{}` has "
            "already been loaded".format(proj_path, _LOADED_PATH)
        )

    if str(proj_path) not in sys.path:
        sys.path.append(str(proj_path))

    kedro_cli = importlib.import_module("kedro_cli")
    result = kedro_cli.__get_kedro_context__()
    _LOADED_PATH = proj_path
    os.chdir(str(proj_path))  # Move to project root
    return result
