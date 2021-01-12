# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=import-outside-toplevel,global-statement,invalid-name
"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""
import logging.config
import sys
from pathlib import Path

from IPython import get_ipython
from IPython.core.magic import needs_local_scope, register_line_magic

project_path = Path.cwd()
catalog = None
context = None
session = None


def _remove_cached_modules(package_name):
    to_remove = [mod for mod in sys.modules if mod.startswith(package_name)]
    # `del` is used instead of `reload()` because: If the new version of a module does not
    # define a name that was defined by the old version, the old definition remains.
    for module in to_remove:
        del sys.modules[module]  # pragma: no cover


def _clear_hook_manager():
    from kedro.framework.hooks import get_hook_manager

    hook_manager = get_hook_manager()
    name_plugin_pairs = hook_manager.list_name_plugin()
    for name, plugin in name_plugin_pairs:
        hook_manager.unregister(name=name, plugin=plugin)  # pragma: no cover


def load_kedro_objects(path, line=None):  # pylint: disable=unused-argument
    """Line magic which reloads all Kedro default variables."""

    import kedro.config.default_logger  # noqa: F401 # pylint: disable=unused-import
    from kedro.framework.cli import load_entry_points
    from kedro.framework.cli.utils import _add_src_to_path
    from kedro.framework.session import KedroSession
    from kedro.framework.session.session import _activate_session
    from kedro.framework.startup import _get_project_metadata

    global context
    global catalog
    global session

    path = path or project_path
    metadata = _get_project_metadata(path)
    _add_src_to_path(metadata.source_dir, path)

    _clear_hook_manager()

    _remove_cached_modules(metadata.package_name)

    session = KedroSession.create(metadata.package_name, path)
    _activate_session(session)
    logging.debug("Loading the context from %s", str(path))
    context = session.load_context()
    catalog = context.catalog

    get_ipython().push(
        variables={"context": context, "catalog": catalog, "session": session}
    )

    logging.info("** Kedro project %s", str(metadata.project_name))
    logging.info("Defined global variable `context`, `session` and `catalog`")

    for line_magic in load_entry_points("line_magic"):
        register_line_magic(needs_local_scope(line_magic))
        logging.info("Registered line magic `%s`", line_magic.__name__)


def init_kedro(path=""):
    """Line magic to set path to Kedro project.
    `%reload_kedro` will default to this location.
    """
    global project_path
    if path:
        project_path = Path(path).expanduser().resolve()
        logging.info("Updated path to Kedro project: %s", str(project_path))
    else:
        logging.info("No path argument was provided. Using: %s", str(project_path))


def load_ipython_extension(ipython):
    """Main entry point when %load_ext is executed"""
    ipython.register_magic_function(init_kedro, "line")
    ipython.register_magic_function(load_kedro_objects, "line", "reload_kedro")

    try:
        load_kedro_objects(project_path)
    except (ImportError, ModuleNotFoundError):
        logging.error("Kedro appears not to be installed in your current environment.")
    except Exception:  # pylint: disable=broad-except
        logging.error(
            "Could not register Kedro extension. Make sure you're in a valid Kedro project.",
            exc_info=True,
        )
