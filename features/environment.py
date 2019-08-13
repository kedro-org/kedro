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

"""Behave environment setup commands."""

import glob
import os
import shutil
import stat
import tempfile
from pathlib import Path

from features.steps.sh_run import run
from features.steps.util import create_new_venv


def before_all(context):
    """Environment preparation before other cli tests are run.
    Installs kedro by running pip in the top level directory.
    """

    def call(cmd):
        res = run(cmd, env=context.env)
        if res.returncode:
            print(res.stdout)
            print(res.stderr)
            assert False

    # make a venv
    if "E2E_VENV" in os.environ:
        context.venv_dir = Path(os.environ["E2E_VENV"])
    else:
        context.venv_dir = Path(create_new_venv())

    # note the locations of some useful stuff
    # this is because exe resolution in supbrocess doens't respect a passed env
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

    # clone the environment, remove any condas and venvs and insert our venv
    context.env = os.environ.copy()
    path = context.env["PATH"].split(path_sep)
    path = [p for p in path if not (Path(p).parent / "pyvenv.cfg").is_file()]
    path = [p for p in path if not (Path(p).parent / "conda-meta").is_dir()]
    path = [str(bin_dir)] + path
    context.env["PATH"] = path_sep.join(path)

    # install Kedro
    call([context.python, "-m", "pip", "install", "-U", "pip"])
    for wheel_path in Path("dist").glob("*.whl"):
        wheel_path.unlink()
    call([context.pip, "install", "wheel"])
    call([context.python, "setup.py", "clean", "--all", "bdist_wheel"])
    call([context.pip, "install", "-U"] + glob.glob("dist/*.whl"))


def after_all(context):
    if "E2E_VENV" not in os.environ:
        rmtree(context.venv_dir)


def before_scenario(context, feature):
    # pylint: disable=unused-argument
    context.temp_dir = Path(tempfile.mkdtemp())


def after_scenario(context, feature):
    # pylint: disable=unused-argument
    rmtree(context.temp_dir)


def rmtree(top):
    """This is for Windows machine to switch the permission."""
    if os.name != "posix":
        for root, _, files in os.walk(str(top), topdown=False):
            for name in files:
                os.chmod(os.path.join(root, name), stat.S_IWUSR)
    shutil.rmtree(str(top))
