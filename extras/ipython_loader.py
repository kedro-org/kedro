# Copyright 2020 QuantumBlack Visual Analytics Limited
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
This script helps to locate IPython startup directory and run all Python scripts in
it when working with Jupyter Notebooks and IPython sessions.
"""

import contextlib
import pathlib
import typing
from warnings import warn


def locate_ipython_startup_dir(
    start_dir: typing.Union[pathlib.Path, str] = None
) -> typing.Union[pathlib.Path, None]:
    """Locate `.ipython` directory recursively starting from `start_dir` directory
    and going up the directory tree.

    Args:
        start_dir: The directory where the search starts. Defaults to the current
            working directory.

    Returns:
        Path to `.ipython/profile_default/startup` directory or None if
            that has not been found.

    """
    this_script_dir = pathlib.Path(__file__).parent.resolve()
    current_dir = pathlib.Path(start_dir or pathlib.Path.cwd()).expanduser().resolve()

    while True:
        startup_dir = current_dir / ".ipython" / "profile_default" / "startup"
        if startup_dir.is_dir() and startup_dir != this_script_dir:
            return startup_dir
        if current_dir.parent == current_dir:
            break  # reached the root of the file system
        current_dir = current_dir.parent
    return None


@contextlib.contextmanager
def modify_globals(**kwargs: typing.Any):
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


def run_startup_scripts(startup_dir: pathlib.Path):
    """Run all Python scripts from the startup directory.

    Args:
        startup_dir: Path to IPython startup directory.

    """
    # pylint: disable=import-outside-toplevel
    import logging
    from sys import stdout

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=fmt, stream=stdout)

    startup_dir = startup_dir.resolve()
    startup_scripts = sorted(f_ for f_ in startup_dir.rglob("*.py") if f_.is_file())

    for script in startup_scripts:
        with modify_globals(__file__=str(script)):
            try:
                compiled = compile(
                    script.read_text(encoding="utf-8"), str(script), "exec"
                )
                exec(compiled, globals())  # pylint: disable=exec-used
            except Exception as err:  # pylint: disable=broad-except
                logging.error(
                    "Startup script `%s` failed:\n%s: %s",
                    str(script),
                    err.__class__.__name__,
                    str(err),
                )
            else:
                logging.info("Startup script `%s` successfully executed", str(script))


def main():
    """Locate IPython startup directory and run all Python scripts in it."""
    warn(
        "This script will be deprecated in future releases. Please refer "
        "to replacement script in kedro/extras/ipython/.",
        DeprecationWarning,
    )
    startup_dir = locate_ipython_startup_dir()
    if startup_dir:
        run_startup_scripts(startup_dir)


if __name__ == "__main__":  # pragma: no cover
    main()

    # cleanup the global scope
    del contextlib, pathlib, typing
    del locate_ipython_startup_dir, modify_globals, run_startup_scripts, main
