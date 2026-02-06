import pytest

from kedro.pipeline import node


@pytest.fixture
def mocked_dataset(mocker, persistent_test_dataset):
    load = mocker.Mock(return_value=42)
    save = mocker.Mock()
    return persistent_test_dataset(load, save)


def one_in_one_out(arg):
    return arg


def one_in_dict_out(arg):
    return {"ret": arg}


def two_in_first_out(arg1, arg2):
    return arg1


@pytest.fixture
def valid_nodes_with_inputs():
    return [
        (node(one_in_one_out, "ds1", "dsOut"), {"ds1": 42}),
        (node(one_in_dict_out, {"arg": "ds1"}, {"ret": "dsOut"}), {"ds1": 42}),
        (node(two_in_first_out, ["ds1", "ds2"], "dsOut"), {"ds1": 42, "ds2": 58}),
    ]


def test_valid_nodes(valid_nodes_with_inputs):
    """Check if node.run works as expected."""
    for node_, input_ in valid_nodes_with_inputs:
        output = node_.run(input_)
        assert output["dsOut"] == 42


def test_run_got_dataframe(mocked_dataset):
    """Check an exception when non-dictionary (class object) is passed."""
    pattern = r"Node.run\(\) expects a dictionary or None, "
    pattern += r"but got <class \'tests.conftest.PersistentTestDataset\'> instead"
    with pytest.raises(ValueError, match=pattern):
        node(one_in_one_out, {"arg": "ds1"}, "A").run(mocked_dataset)


class TestNodeRunInvalidInput:
    def test_unresolved(self):
        """Pass no input when one is expected."""
        with pytest.raises(ValueError, match=r"expected one input"):
            node(one_in_one_out, "unresolved", "ds1").run(None)

    def test_no_inputs_node_error(self, mocked_dataset):
        """Pass one input when none is expected."""
        with pytest.raises(ValueError, match=r"expected no inputs"):
            node(lambda: 1, None, "A").run({"unexpected": mocked_dataset})

    def test_one_input_error(self, mocked_dataset):
        """Pass a different input."""
        pattern = r"expected one input named 'ds1', but got the "
        pattern += r"following 1 input\(s\) instead: \['arg'\]"
        with pytest.raises(ValueError, match=pattern):
            node(one_in_dict_out, "ds1", {"ret": "B", "ans": "C"}).run(
                {"arg": mocked_dataset}
            )

    def test_run_diff_size_lists(self, mocked_dataset):
        """Pass only one dict input when two (list) are expected."""
        pattern = r"expected 2 input\(s\) \['ds1', 'ds2'\], but "
        pattern += r"got the following 1 input\(s\) instead."
        with pytest.raises(ValueError, match=pattern):
            node(two_in_first_out, ["ds1", "ds2"], "A").run({"ds1": mocked_dataset})

    def test_run_diff_size_list_dict(self, mocked_dataset):
        """Pass two dict inputs when one (list) are expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 2 input\(s\) instead: \['ds1', 'ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, ["ds1"], "A").run({"ds1": mocked_dataset, "ds2": 2})

    def test_run_list_dict_unavailable(self, mocked_dataset):
        """Pass one dict which is different from expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 1 input\(s\) instead: \['ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, ["ds1"], "A").run({"ds2": mocked_dataset})

    def test_run_dict_unavailable(self, mocked_dataset):
        """Pass one dict which is different from expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 1 input\(s\) instead: \['ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, {"arg": "ds1"}, "A").run({"ds2": mocked_dataset})

    def test_run_dict_diff_size(self, mocked_dataset):
        """Pass two dict inputs when one is expected."""
        pattern = r"expected 1 input\(s\) \['ds1'\], but got the "
        pattern += r"following 2 input\(s\) instead: \['ds1', 'ds2'\]\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, {"arg": "ds1"}, "A").run(
                {"ds1": mocked_dataset, "ds2": 2}
            )


class TestNodeRunInvalidOutput:
    def test_miss_matching_output_types(self, mocked_dataset):
        pattern = "The node output is a dictionary, whereas the function "
        pattern += "output is <class 'tests.conftest.PersistentTestDataset'>."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, "ds1", {"a": "ds"}).run({"ds1": mocked_dataset})

    def test_miss_matching_output_keys(self, mocked_dataset):
        pattern = r"The node's output keys {'ret'} do not match "
        pattern += r"with the returned output's keys"
        with pytest.raises(ValueError, match=pattern):
            node(one_in_dict_out, "ds1", {"ret": "B", "ans": "C"}).run(
                {"ds1": mocked_dataset}
            )

    def test_node_not_list_output(self, mocked_dataset):
        pattern = r"The node definition contains a list of outputs "
        pattern += r"\['B', 'C'\], whereas the node function returned "
        pattern += r"a 'PersistentTestDataset'"
        with pytest.raises(ValueError, match=pattern):
            node(one_in_one_out, "ds1", ["B", "C"]).run({"ds1": mocked_dataset})

    def test_node_wrong_num_of_outputs(
        self, mocker, mocked_dataset, persistent_test_dataset
    ):
        def one_in_two_out(arg):
            load = mocker.Mock(return_value=42)
            save = mocker.Mock()
            return [
                persistent_test_dataset(load, save),
                persistent_test_dataset(load, save),
            ]

        pattern = r"The node function returned 2 output\(s\), whereas "
        pattern += r"the node definition contains 3 output\(s\)\."
        with pytest.raises(ValueError, match=pattern):
            node(one_in_two_out, "ds1", ["A", "B", "C"]).run({"ds1": mocked_dataset})


class TestNodeOutputsNoneWarning:
    """Test warning behavior when outputs=None but function returns a value."""

    @pytest.mark.parametrize(
        "return_value,expected_type",
        [
            ({"r2_score": 0.95}, "dict"),
            ([1, 2, 3], "list"),
            (42, "int"),
        ],
    )
    def test_outputs_none_warns_when_value_returned(self, return_value, expected_type):
        def func(_):
            return return_value

        test_node = node(func, "input", None, name="test_node")
        pattern = (
            rf"Node 'test_node' returned a value of type '{expected_type}', "
            rf"but outputs=None\. This value will not be included in the "
            rf"pipeline outputs\. To keep it, specify outputs in the node definition\."
        )
        with pytest.warns(UserWarning, match=pattern):
            test_node.run({"input": 42})

    def test_outputs_none_does_not_warn_when_none_returned(self):
        def func(_):
            return None

        test_node = node(func, "input", None, name="test_node")
        with pytest.warns(None):
            result = test_node.run({"input": 42})
        assert result == {}
