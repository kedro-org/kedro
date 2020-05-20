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

"""This file has been deprecated and will be deleted in 0.17.0.
Please make any additional changes in `kedro.framework.cli.jupyter.py` instead.
"""


from jupyter_client.kernelspec import NATIVE_KERNEL_NAME, KernelSpecManager
from traitlets import Unicode

from kedro.cli import load_entry_points


def collect_line_magic():
    """Interface function for collecting line magic functions from plugin entry points.
    """
    return load_entry_points("line_magic")


class SingleKernelSpecManager(KernelSpecManager):
    """A custom KernelSpec manager to be used by Kedro projects.
    It limits the kernels to the default one only,
    to make it less confusing for users, and gives it a sensible name.
    """

    default_kernel_name = Unicode(
        "Kedro", config=True, help="Alternative name for the default kernel"
    )
    whitelist = [NATIVE_KERNEL_NAME]

    def get_kernel_spec(self, kernel_name):
        """
        This function will only be called by Jupyter to get a KernelSpec
        for the default kernel.
        We replace the name by something sensible here.
        """
        kernelspec = super().get_kernel_spec(kernel_name)

        if kernel_name == NATIVE_KERNEL_NAME:
            kernelspec.display_name = self.default_kernel_name

        return kernelspec
