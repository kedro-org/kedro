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
Black needs python 3.6+, but Kedro should work on 3.5 too,
that's why we can't put ``black`` into test_requirements.txt and
have to install it manually like that.

If python version is 3.5 - just exit with 0 status.
"""
import platform
import shlex
import subprocess
import sys

if __name__ == "__main__":
    required_version = tuple(int(x) for x in sys.argv[1].strip().split("."))
    install_cmd = shlex.split(sys.argv[2])
    run_cmd = shlex.split(sys.argv[3])

    current_version = tuple(map(int, platform.python_version_tuple()[:2]))

    if current_version < required_version:
        print("Python version is too low, exiting")
        sys.exit(0)

    try:
        subprocess.run(run_cmd, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run(install_cmd, check=True)
        subprocess.run(run_cmd, check=True)
