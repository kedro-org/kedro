# Copyright 2021 QuantumBlack Visual Analytics Limited
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
"""Script that is called after the user fills in the cookiecutter prompts,
found in `starter_config.yml`, but before the folders are created.
See https://cookiecutter.readthedocs.io/en/1.7.2/advanced/hooks.html for details.
"""
import re
import sys

from click import secho

repo_name = '{{ cookiecutter.repo_name }}'

if not re.match(r"^\w+(-*\w+)*$", repo_name):
    secho(f"`{repo_name}` is not a valid repository name. It must contain "
          f"only word symbols and/or hyphens, must also start and "
          f"end with alphanumeric symbol.", fg="red", err=True)
    # exits with status 1 to indicate failure
    sys.exit(1)


pkg_name = "{{ cookiecutter.python_package }}"
base_message = f"`{pkg_name}` is not a valid Python package name."

if not re.match(r"^[a-zA-Z_]", pkg_name):
    secho(base_message + " It must start with a letter or underscore.", fg="red", err=True)
    sys.exit(1)
if len(pkg_name) < 2:
    secho(base_message + " It must be at least 2 characters long.", fg="red", err=True)
    sys.exit(1)
if not re.match(r"^\w+$", pkg_name[1:]):
    secho(base_message + " It must contain only letters, digits, and/or underscores.", fg="red", err=True)
    sys.exit(1)
