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
import pytest

from kedro.framework.project.settings import _get_project_settings


# pylint: disable=attribute-defined-outside-init,too-few-public-methods
class TestSettings:
    pass


class TestGetSettings:
    default_value = "default_value"
    property_name = "property_name"
    package_name = "package_name"

    def test_settings_py_is_missing(self):
        with pytest.raises(ModuleNotFoundError):
            _get_project_settings(
                self.package_name, self.property_name, self.default_value
            )

    def test_property_is_missing(self, mocker):
        mocker.patch(
            "kedro.framework.project.settings.import_module",
            return_value=TestSettings(),
        )

        value = _get_project_settings(
            self.package_name, self.property_name, self.default_value
        )

        assert value == self.default_value

    def test_get_project_settings(self, mocker):
        property_value = "property_value"

        settings_obj = TestSettings()
        settings_obj.property_name = property_value
        mocker.patch(
            "kedro.framework.project.settings.import_module", return_value=settings_obj
        )

        value = _get_project_settings(
            self.package_name, self.property_name, self.default_value
        )

        assert value == property_value
