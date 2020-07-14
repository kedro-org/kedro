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
"""Behave environment setup commands."""
# pylint: disable=unused-argument

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path
from typing import Set

import clonevirtualenv

from features.steps.sh_run import run

_PATHS_TO_REMOVE = set()  # type: Set[Path]

FRESH_VENV_TAG = "fresh_venv"
# Used in rmtree in after_scenario and after_all
# When doing a couple of test runs, no more than 10 retries were necessary for rmtree to succeed.
MAX_RETRIES = 12


# monkeypatch https://github.com/edwardgeorge/virtualenv-clone/blob/master/clonevirtualenv.py#L50
# work on Windows by passing in required environment variables to the underlying Python subprocess
def _fake_virtualenv_sys(venv_path):
    "Obtain Python version and path info from a virtualenv."
    env_bin_dir = "Scripts" if sys.platform.startswith("win") else "bin"

    executable = os.path.join(venv_path, env_bin_dir, "python")
    # Must use "executable" as the first argument rather than as the
    # keyword argument "executable" to get correct value from sys.path
    pipe = subprocess.Popen(
        [
            executable,
            "-c",
            "import sys;"
            + "print (sys.version[:3]);"
            + 'print ("\\n".join(sys.path));',
        ],
        # Windows requires PYTHONHASHSEED to be set to initialise Python
        # and requires the PATH variable to be set
        env={"PYTHONHASHSEED": "1", "PATH": ""},
        stdout=subprocess.PIPE,
    )
    stdout, _ = pipe.communicate()
    assert not pipe.returncode and stdout, stdout
    lines = stdout.decode("utf-8").splitlines()
    python_version = lines[0]
    sys_path = list(filter(bool, lines[1:]))
    return python_version, sys_path


clonevirtualenv._virtualenv_sys = (  # pylint: disable=protected-access
    _fake_virtualenv_sys
)


def call(cmd, env):
    res = run(cmd, env=env)
    if res.returncode:
        print(res.stdout)
        print(res.stderr)
        assert False


def before_all(context):
    """Environment preparation before other cli tests are run.
    Installs (core) kedro by running pip in the top level directory.
    """
    context = _setup_base_venv(context)
    context = _setup_kedro_install_venv(context)


def after_all(context):
    for path in _PATHS_TO_REMOVE:
        rmtree(path)


def before_scenario(context, scenario):
    if FRESH_VENV_TAG in scenario.tags:
        new_venv_dir = _create_tmp_dir() / "temp"
        # need to use virtualenv-clone instead of just a bare copy to resolve sys.paths and the like
        clonevirtualenv.clone_virtualenv(str(context.base_venv_dir), str(new_venv_dir))

        context = _setup_context_with_venv(context, new_venv_dir)
    elif os.name != "posix":
        # On Windows virtual env cloning doesn't work properly.
        # This is a temporary workaround to make several tests pass.
        context = _setup_kedro_install_venv(context)
    context.temp_dir = Path(tempfile.mkdtemp())


def after_scenario(context, scenario):
    if FRESH_VENV_TAG in scenario.tags:
        rmtree(context.venv_dir)
        context = _setup_context_with_venv(context, context.kedro_install_venv_dir)
    rmtree(context.temp_dir)


def rmtree(top):
    """This is for Windows machine to switch the permission."""
    if os.name != "posix":
        for root, _, files in os.walk(str(top), topdown=False):
            for name in files:
                os.chmod(os.path.join(root, name), stat.S_IWUSR)

    times_retried = 0
    while times_retried < MAX_RETRIES:
        try:
            shutil.rmtree(top)
            break
        except Exception as err:  # pylint: disable=broad-except
            print(err)
            times_retried += 1
            time.sleep(2)


def _setup_context_with_venv(context, venv_dir):
    context.venv_dir = venv_dir
    # note the locations of some useful stuff
    # this is because exe resolution in subprocess doesn't respect a passed env
    if os.name == "posix":
        bin_dir = context.venv_dir / "bin"
        path_sep = ":"
    else:
        bin_dir = context.venv_dir / "Scripts"
        path_sep = ";"
    context.bin_dir = bin_dir
    context.pip = str(bin_dir / "pip")
    context.python = str(bin_dir / "python")
    context.kedro = str(bin_dir / "kedro")
    context.requirements_path = Path("requirements.txt").resolve()

    # clone the environment, remove any condas and venvs and insert our venv
    context.env = os.environ.copy()
    path = context.env["PATH"].split(path_sep)
    path = [p for p in path if not (Path(p).parent / "pyvenv.cfg").is_file()]
    path = [p for p in path if not (Path(p).parent / "conda-meta").is_dir()]
    path = [str(bin_dir)] + path
    context.env["PATH"] = path_sep.join(path)

    # Create an empty pip.conf file and point pip to it
    pip_conf_path = context.venv_dir / "pip.conf"
    pip_conf_path.touch()
    context.env["PIP_CONFIG_FILE"] = str(pip_conf_path)

    return context


def _create_new_venv() -> Path:
    """Create a new venv.

    Returns:
        path to created venv
    """
    # Create venv
    venv_dir = _create_tmp_dir()
    venv.main([str(venv_dir)])
    return venv_dir


def _create_tmp_dir() -> Path:
    """Create a temp directory and add it to _PATHS_TO_REMOVE"""
    tmp_dir = Path(tempfile.mkdtemp()).resolve()
    _PATHS_TO_REMOVE.add(tmp_dir)
    return tmp_dir


def _setup_base_venv(context):
    # make a venv
    venv_dir = _create_new_venv()

    context.base_venv_dir = venv_dir
    context = _setup_context_with_venv(context, venv_dir)

    # install Kedro
    # these versions should match what's in the Makefile
    call(
        [
            context.python,
            "-m",
            "pip",
            "install",
            "-U",
            "pip>=20.0, <21.0",
            "setuptools>=38.0, <47.0",
            "wheel",
        ],
        env=context.env,
    )
    call([context.pip, "install", "."], env=context.env)

    return context


def _setup_kedro_install_venv(context):
    kedro_install_venv_dir = _create_tmp_dir() / "ked-install"
    # need to use virtualenv-clone instead of just a bare copy to resolve sys.paths and the like
    clonevirtualenv.clone_virtualenv(
        str(context.base_venv_dir), str(kedro_install_venv_dir)
    )
    context.kedro_install_venv_dir = kedro_install_venv_dir
    context = _setup_context_with_venv(context, kedro_install_venv_dir)
    install_reqs = (
        Path(
            "kedro/templates/project/{{ cookiecutter.repo_name }}/src/requirements.txt"
        )
        .read_text()
        .splitlines()
    )
    install_reqs = [req for req in install_reqs if "{" not in req]
    install_reqs.append(".[pandas.CSVDataSet]")

    call([context.pip, "install", *install_reqs], env=context.env)
    return context
