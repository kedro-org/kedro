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
import re

import pytest
import yaml

from kedro.framework.cli.utils import get_source_dir


@pytest.fixture(params=[None])
def fake_kedro_yml(request, tmp_path):
    kedro_yml = tmp_path / ".kedro.yml"
    payload = request.param or dict()

    with kedro_yml.open("w") as _f:
        yaml.safe_dump(payload, _f)

    return kedro_yml


@pytest.mark.parametrize(
    "fake_kedro_yml,expected_source_dir",
    [(None, "src"), ({"source_dir": "some/nested/dir"}, "some/nested/dir")],
    indirect=["fake_kedro_yml"],
)
def test_get_source_dir(tmp_path, fake_kedro_yml, expected_source_dir):
    expected_source_dir = (tmp_path / expected_source_dir).resolve()
    assert fake_kedro_yml.is_file()

    pattern = "This function is now deprecated and will be removed in Kedro 0.17.0"
    with pytest.warns(DeprecationWarning, match=re.escape(pattern)):
        src_dir = get_source_dir(tmp_path)

    assert src_dir == expected_source_dir
