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

# pylint: disable=unused-argument

import pytest

from kedro.io import LambdaDataSet
from kedro.pipeline import node


@pytest.fixture
def mocked_dataset(mocker):
    load = mocker.Mock(return_value=42)
    save = mocker.Mock()
    return LambdaDataSet(load, save)


def one_in_one_out(arg):
    return arg


def one_in_dict_out(arg):
    return dict(ret=arg)


def two_in_first_out(arg1, arg2):
    return arg1


@pytest.fixture
def valid_nodes_with_inputs():
    return [
        (node(one_in_one_out, "ds1", "dsOut"), dict(ds1=42)),
        (node(one_in_dict_out, dict(arg="ds1"), dict(ret="dsOut")), dict(ds1=42)),
        (node(two_in_first_out, ["ds1", "ds2"], "dsOut"), dict(ds1=42, ds2=58)),
    ]


def test_valid_nodes(valid_nodes_with_inputs):
    """Check if node.run works as expected."""
    for node_, input_ in valid_nodes_with_inputs:
        output = node_.run(input_)
        assert output["dsOut"] == 42


def test_run_got_dataframe(mocked_dataset):
    """Check an exception when non-dictionary (class object) is passed."""
    pattern = r"Node.run\(\) expects a dictionary or None, "
    pattern += r"but got <class \'kedro.io.lambda_data_set.LambdaDataSet\'> instead"
    with pytest.raises(ValueError, match=pattern):
        node(one_in_one_out, dict(arg="ds1"), "A").run(mocked_dataset)


class TestNodeRunInvalidInput:
    def test_unresolved(self):
        """Pass no input when one is expected."""
        with pytest.raises(ValueError, match=r"expected one input"):
            node(one_in_one_out, "unresolved", "ds1").run(None)

    def test_no_inputs_node_error(self, mocked_dataset):
        """Pass one input when none is expected."""
        with pytest.raises(ValueError, match=r"expected no inputs"):
            node(lambda: 1, None, "A").run(dict(unexpected=mocked_dataset))

    def test_one_input_error(self, mocked_dataset):
        """Pass a different input."""
        pattern = r"expected one input named 'ds1', but got the "
        pattern += r"following 1 input\(s\) instead: \['arg'\]"
        with pytest.raises(ValueError, match=pattern):
            node(one_in_dict_out, "ds1", dict(ret="B", ans="C")).run(
                dict(arg=mocked_dataset)
            )

    def test_run_diff_size_lists(self, mocked_dataset):
        """Pass only one dict input when two (list) are expected."""
        pattern = r"expected 2 input\(s\) \['ds1', 'ds2'\], but "
        pattern += r"got the following 1 input\(s\) instead."
        with pytest.raises(ValueError, match=pattern):
            node(two_in_first_out, ["ds1", "ds2"], "A").run(dict(ds1=mocked_dataset))

    def test_run_diff_size_list_dict(self, mocked_dataset):
        """Pass two dict inputs when one (list) are expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 2 input\(s\) instead: \['ds1', 'ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, ["ds1"], "A").run(dict(ds1=mocked_dataset, ds2=2))

    def test_run_list_dict_unavailable(self, mocked_dataset):
        """Pass one dict which is different from expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 1 input\(s\) instead: \['ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, ["ds1"], "A").run(dict(ds2=mocked_dataset))

    def test_run_dict_unavailable(self, mocked_dataset):
        """Pass one dict which is different from expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 1 input\(s\) instead: \['ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, dict(arg="ds1"), "A").run(dict(ds2=mocked_dataset))

    def test_run_dict_diff_size(self, mocked_dataset):
        """Pass two dict inputs when one is expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 2 input\(s\) instead: \['ds1', 'ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, dict(arg="ds1"), "A").run(
                dict(ds1=mocked_dataset, ds2=2)
            )


class TestNodeRunInvalidOutput:
    def test_miss_matching_output_types(self, mocked_dataset):
        pattern = r"The node output is a dictionary, whereas the function "
        pattern += r"output is not\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, "ds1", dict(a="ds")).run(dict(ds1=mocked_dataset))

    def test_miss_matching_output_keys(self, mocked_dataset):
        pattern = r"The node's output keys {'ret'} do not match "
        pattern += r"with the returned output's keys"
        with pytest.raises(ValueError, match=pattern):
            node(one_in_dict_out, "ds1", dict(ret="B", ans="C")).run(
                dict(ds1=mocked_dataset)
            )

    def test_node_not_list_output(self, mocked_dataset):
        pattern = r"The node definition contains a list of outputs "
        pattern += r"\['B', 'C'\], whereas the node function returned "
        pattern += r"a `LambdaDataSet`"
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, "ds1", ["B", "C"]).run(dict(ds1=mocked_dataset))

    def test_node_wrong_num_of_outputs(self, mocker, mocked_dataset):
        def one_in_two_out(arg):
            load = mocker.Mock(return_value=42)
            save = mocker.Mock()
            return [LambdaDataSet(load, save), LambdaDataSet(load, save)]

        pattern = r"The node function returned 2 output\(s\), whereas "
        pattern += r"the node definition contains 3 output\(s\)\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_two_out, "ds1", ["A", "B", "C"]).run(dict(ds1=mocked_dataset))
