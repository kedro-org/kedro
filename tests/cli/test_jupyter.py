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

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME, KernelSpecManager

from kedro.cli.jupyter import SingleKernelSpecManager, collect_line_magic


def test_collect_line_magic(entry_points, entry_point):
    entry_point.load.return_value = "line_magic"
    line_magics = collect_line_magic()
    assert line_magics == ["line_magic"]
    entry_points.assert_called_once_with(group="kedro.line_magic")


class TestSingleKernelSpecManager:
    def test_overridden_values(self):
        assert SingleKernelSpecManager.whitelist == [NATIVE_KERNEL_NAME]

    def test_renaming_default_kernel(self, mocker):
        """
        Make sure the default kernel display_name is changed.
        """
        mocker.patch.object(
            KernelSpecManager,
            "get_kernel_spec",
            return_value=mocker.Mock(display_name="default"),
        )
        manager = SingleKernelSpecManager()
        manager.default_kernel_name = "New Kernel Name"
        new_kernel_spec = manager.get_kernel_spec(NATIVE_KERNEL_NAME)
        assert new_kernel_spec.display_name == "New Kernel Name"

    def test_non_default_kernel_untouched(self, mocker):
        """
        Make sure the non-default kernel display_name is not changed.
        In theory the function will never be called like that,
        but let's not make extra assumptions.
        """
        mocker.patch.object(
            KernelSpecManager,
            "get_kernel_spec",
            return_value=mocker.Mock(display_name="default"),
        )
        manager = SingleKernelSpecManager()
        manager.default_kernel_name = "New Kernel Name"
        new_kernel_spec = manager.get_kernel_spec("another_kernel")
        assert new_kernel_spec.display_name == "default"
