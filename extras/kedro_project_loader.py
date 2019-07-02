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

"""
This script helps to locate Kedro project and run IPython startup scripts in
it when working with Jupyter Notebooks and IPython sessions.
"""

import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Union

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stdout
)


def locate_project_root(start_dir: Path = None) -> Union[Path, None]:
    """Locate Kedro project root directory recursively starting from `start_dir`
    directory. Kedro project must contain `kedro_cli.py` file in its root directory
    to be successfully identified.

    Args:
        start_dir: The directory where the search starts.
            Defaults to the current working directory.

    Returns:
        Path to Kedro project root directory or None if Kedro project hasn't been found.

    """
    current_dir = (start_dir or Path.cwd()).resolve()

    while True:
        if (current_dir / "kedro_cli.py").is_file():
            return current_dir
        if current_dir.parent == current_dir:
            # current_dir is the root of the file system
            break
        current_dir = current_dir.parent
    return None


@contextmanager
def modify_globals(**kwargs: Any):
    """Temporarily modifies globals() before they are passed to exec().

    Args:
        kwargs: New keys to add/modify in the globals.

    Yields:
        None: None.
    """
    globals_ = globals()
    overwritten = {k: globals_[k] for k in globals_.keys() & kwargs.keys()}
    try:
        globals_.update(kwargs)
        yield
    finally:
        for var in kwargs:
            globals_.pop(var, None)
        globals_.update(overwritten)


load_kedro_errors = dict()  # pylint: disable=invalid-name


def startup_kedro_project(project_dir: Path):
    """Run all Python scripts from `<project_dir>/.ipython/profile_default/startup`
    directory.

    Args:
        project_dir: Path to Kedro project root directory.

    """
    project_dir = project_dir.resolve()
    ipython_dir = project_dir / ".ipython" / "profile_default" / "startup"
    for script in sorted(ipython_dir.rglob("*.py")):
        if script.is_file():
            with modify_globals(__file__=str(script)):
                try:
                    _compiled = compile(
                        script.read_text(encoding="utf-8"), str(script), "exec"
                    )
                    exec(_compiled, globals())  # pylint: disable=exec-used
                except Exception as err:  # pylint: disable=broad-except
                    load_kedro_errors[str(script)] = err
                    msg = "Startup script `%s` failed:\n%s"
                    logging.error(msg, str(script), str(err))
                else:
                    msg = "Successfully executed startup script `%s`"
                    logging.info(msg, str(script))


def main():
    """Locate Kedro project and run IPython startup scripts in it."""
    kedro_dir = locate_project_root()
    if kedro_dir:
        startup_kedro_project(kedro_dir)


if __name__ == "__main__":
    main()  # pragma: no cover
