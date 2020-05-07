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

import pandas as pd
import pytest
from pydantic import (  # pylint: disable=no-name-in-module
    BaseModel,
    ValidationError,
    confloat,
)

from kedro.extras.decorators.validate_inputs import validate


class SplitFracShuffle(BaseModel):  # pylint: disable=too-few-public-methods
    frc: confloat(strict=True, gt=0, lt=1)  # type: ignore
    shuffle: bool


@pytest.fixture
def myfn():
    def test(
        a: SplitFracShuffle, df: pd.DataFrame, c: str
    ):  # pylint: disable=unused-argument
        return a

    return test


@pytest.mark.parametrize(
    "arguments,inputs",
    [
        (["a"], ({"frc": 0.5, "shuffle": "Y"}, 2.0, 1)),
        (["c"], (2.0, 1, "a")),
        (["a", "c"], ({"frc": 0.5, "shuffle": True}, 2.0, "a")),
    ],
)
def test_parse_type_and_validate(myfn, arguments, inputs):
    a = validate(*arguments)(myfn)(*inputs)
    if "a" in arguments:
        assert a.shuffle is True


@pytest.mark.parametrize(
    "arguments,inputs",
    [(["a"], ({"frc": 2.0, "shuffle": "Y"}, "a", 1)), (["c"], (2.0, 1, []))],
)
def test_wrong_type_val(myfn, arguments, inputs):
    with pytest.raises(ValidationError):
        validate(*arguments)(myfn)(*inputs)
