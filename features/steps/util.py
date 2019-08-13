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

"""Common functions for e2e testing.
"""

import os
import re
import tempfile
import venv
from contextlib import contextmanager
from pathlib import Path
from time import sleep, time
from typing import Any, Callable, Iterator, List

import pandas as pd


def get_sample_csv_content():
    return """col1, col2, col3
    1, 2, 3
    4, 5, 6
    """


def get_sample_data_frame():
    data = {"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]}
    return pd.DataFrame(data)


def create_temp_csv():
    _, csv_file_path = tempfile.mkstemp(suffix=".csv")
    return csv_file_path


def create_sample_csv():
    csv_file_path = create_temp_csv()
    with open(csv_file_path, mode="w") as output_file:
        output_file.write(get_sample_csv_content())
    return csv_file_path


@contextmanager
def chdir(path: Path) -> Iterator:
    # pylint: disable=W9014
    """Context manager to help execute code in a different directory.

    Args:
        path: directory to change to.

    Yields:
        None
    """
    old_pwd = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(old_pwd)


class WaitForException(Exception):
    pass


def wait_for(
    func: Callable,
    timeout_: int = 10,
    print_error: bool = False,
    sleep_for: int = 1,
    **kwargs
) -> Any:
    """Run specified function until it returns expected result until timeout.

    Args:
        func: Specified function.
        timeout_: Time out in seconds. Defaults to 10.
        print_error: whether any exceptions raised should be printed.
            Defaults to False.
        sleep_for: Execute func every specified number of seconds.
            Defaults to 1.
        **kwargs: Arguments to be passed to func.

    Raises:
         WaitForException: if func doesn't return expected result within the
         specified time.

    Returns:
        Function return.

    """
    end = time() + timeout_
    while time() <= end:
        try:
            result = func(**kwargs)
            return result
        except Exception as err:  # pylint: disable=broad-except
            if print_error:
                print(err)

        sleep(sleep_for)
    raise WaitForException(
        "func: %s, didn't return within specified timeout: %d" % (func, timeout_)
    )


def create_new_venv() -> Path:
    """Create a new venv.

    Returns:
        path to created venv
    """
    # Create venv
    venv_dir = Path(tempfile.mkdtemp())
    venv.main([str(venv_dir)])
    return venv_dir


def get_logline_count(logfile: str) -> int:
    """Get line count in logfile

    Note: If logfile doesn't exist will return 0

    Args:
        logfile: path to logfile

    Returns:
        line count of logfile
    """
    try:
        with open(logfile) as file_handle:
            return sum(1 for i in file_handle)
    except FileNotFoundError:
        return 0


def get_last_logline(logfile: str) -> str:
    """Get last line of logfile

    Args:
        logfile: path to logfile

    Returns:
        last line of logfile
    """
    line = ""
    with open(logfile) as file_handle:
        for line in file_handle:
            pass

    return line


def get_logfile_path(proj_dir: Path) -> str:
    """
    Helper function to fet full path of `pipeline.log` inside project

    Args:
        proj_dir: path to proj_dir

    Returns:
        path to `pipeline.log`
    """
    log_file = (proj_dir / "logs" / "visualization" / "pipeline.log").absolute()
    return str(log_file)


def parse_csv(text: str) -> List[str]:
    """Parse comma separated **double quoted** strings in behave steps

    Args:
        text: double quoted comma separated string

    Returns:
        List of string tokens
    """
    return re.findall(r"\"(.+?)\"\s*,?", text)
