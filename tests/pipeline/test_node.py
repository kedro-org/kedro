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
import sys
from functools import partial, update_wrapper, wraps
from typing import Callable

import pytest

from kedro.pipeline import node


# Different dummy func based on the number of arguments
def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


def triconcat(input1: str, input2: str, input3: str):
    return input1 + input2 + input3  # pragma: no cover


def kwarg_node(
    arg1, arg2, *args, arg3, arg_10=0, **extra  # pylint: disable=unused-argument
):
    pass  # pragma: no cover


@pytest.fixture
def simple_tuple_node_list():
    return [
        (identity, "A", "B"),
        (biconcat, ["A", "B"], "C"),
        (identity, "C", ["D", "E"]),
        (biconcat, ["H", "I"], ["J", "K"]),
        (identity, "J", dict(result="K")),
        (biconcat, ["J", "K"], dict(result="L")),
        (identity, dict(input1="J"), "L"),
        (identity, dict(input1="J"), ["L", "M"]),
        (identity, dict(input1="J"), dict(result="K")),
        (constant_output, None, "M"),
        (biconcat, ["N", "O"], None),
        (lambda x: None, "F", "G"),
        (lambda x: ("a", "b"), "G", ["X", "Y"]),
    ]


class TestValidNode:
    def test_valid(self, simple_tuple_node_list):
        nodes = [node(*tup) for tup in simple_tuple_node_list]
        assert len(nodes) == len(simple_tuple_node_list)

    def test_labelled(self):
        assert "labeled_node: <lambda>([input1]) -> [output1]" in str(
            node(lambda x: None, "input1", "output1", name="labeled_node")
        )

    def test_call(self):
        dummy_node = node(
            biconcat, inputs=["input1", "input2"], outputs="output", name="myname"
        )
        actual = dummy_node(input1="in1", input2="in2")
        expected = dummy_node.run(dict(input1="in1", input2="in2"))
        assert actual == expected

    def test_call_with_non_keyword_arguments(self):
        dummy_node = node(
            biconcat, inputs=["input1", "input2"], outputs="output", name="myname"
        )
        pattern = r"__call__\(\) takes 1 positional argument but 2 were given"
        with pytest.raises(TypeError, match=pattern):
            dummy_node("in1", input2="in2")

    def test_no_input(self):
        assert "constant_output(None) -> [output1]" in str(
            node(constant_output, None, "output1")
        )

    def test_no_output(self):
        assert "<lambda>([input1]) -> None" in str(node(lambda x: None, "input1", None))

    def test_inputs_none(self):
        dummy_node = node(constant_output, None, "output")
        assert dummy_node.inputs == []

    def test_inputs_str(self):
        dummy_node = node(identity, "input1", "output1")
        assert dummy_node.inputs == ["input1"]

    def test_inputs_dict(self):
        dummy_node = node(
            biconcat,
            {"input1": "in1", "input2": "in2"},
            ["output2", "output1", "last node"],
        )
        inputs = dummy_node.inputs
        assert isinstance(inputs, list)
        assert len(inputs) == 2
        assert set(inputs) == {"in1", "in2"}

    def test_inputs_dict_order(self):
        dummy = node(
            kwarg_node,
            {"arg5": "a", "arg4": "b", "arg3": "c", "arg2": "d", "arg1": "e"},
            None,
        )
        # a and b and c are keyword args, so they should be sorted
        assert dummy.inputs == ["e", "d", "a", "b", "c"]

    def test_inputs_list(self):
        dummy_node = node(
            triconcat,
            ["input1", "input2", "another node"],
            ["output1", "output2", "last node"],
        )
        assert dummy_node.inputs == ["input1", "input2", "another node"]

    def test_outputs_none(self):
        dummy_node = node(identity, "input", None)
        assert dummy_node.outputs == []

    def test_outputs_str(self):
        dummy_node = node(identity, "input1", "output1")
        assert dummy_node.outputs == ["output1"]

    def test_outputs_dict(self):
        dummy_node = node(
            biconcat, ["input1", "input2"], {"output1": "out1", "output2": "out2"}
        )
        outputs = dummy_node.outputs
        assert isinstance(outputs, list)
        assert len(outputs) == 2
        assert set(outputs) == {"out1", "out2"}

    def test_outputs_list(self):
        dummy_node = node(
            triconcat,
            ["input2", "input1", "another node"],
            ["output2", "output1", "last node"],
        )
        assert dummy_node.outputs == ["output2", "output1", "last node"]


class TestNodeComparisons:
    def test_node_equals(self):
        first = node(identity, "input1", "output1", name="a node")
        second = node(identity, "input1", "output1", name="a node")
        assert first == second
        assert first is not second

    def test_node_less_than(self):
        first = node(identity, "input1", "output1", name="A")
        second = node(identity, "input1", "output1", name="B")
        assert first < second
        assert first is not second

    def test_node_invalid_equals(self):
        n = node(identity, "input1", "output1", name="a node")
        assert n != "hello"

    def test_node_invalid_less_than(self):
        n = node(identity, "input1", "output1", name="a node")
        pattern_36_37 = "'<' not supported between instances of 'Node' and 'str'"
        pattern_35 = "unorderable types"

        pattern = pattern_35 if sys.version_info[:2] == (3, 5) else pattern_36_37
        with pytest.raises(TypeError, match=pattern):
            n < "hello"  # pylint: disable=pointless-statement

    def test_different_input_list_order_not_equal(self):
        first = node(biconcat, ["input1", "input2"], "output1", name="A")
        second = node(biconcat, ["input2", "input1"], "output1", name="A")
        assert first != second

    def test_different_output_list_order_not_equal(self):
        first = node(identity, "input1", ["output1", "output2"], name="A")
        second = node(identity, "input1", ["output2", "output1"], name="A")
        assert first != second

    def test_different_input_dict_order_equal(self):
        first = node(biconcat, {"input1": "a", "input2": "b"}, "output1", name="A")
        second = node(biconcat, {"input2": "b", "input1": "a"}, "output1", name="A")
        assert first == second

    def test_different_output_dict_order_equal(self):
        first = node(identity, "input1", {"output1": "a", "output2": "b"}, name="A")
        second = node(identity, "input1", {"output2": "b", "output1": "a"}, name="A")
        assert first == second

    def test_input_dict_list_not_equal(self):
        first = node(biconcat, ["input1", "input2"], "output1", name="A")
        second = node(
            biconcat, {"input1": "input1", "input2": "input2"}, "output1", name="A"
        )
        assert first != second

    def test_output_dict_list_not_equal(self):
        first = node(identity, "input1", ["output1", "output2"], name="A")
        second = node(
            identity, "input1", {"output1": "output1", "output2": "output2"}, name="A"
        )
        assert first != second


def bad_input_type_node():
    return lambda x: None, ("A", "D"), "B"


def bad_output_type_node():
    return lambda x: None, "A", {"B", "C"}


def bad_function_type_node():
    return "A", "B", "C"


def no_input_or_output_node():
    return constant_output, None, None


def input_same_as_output_node():
    return biconcat, ["A", "B"], dict(a="A")


def duplicate_output_dict_node():
    return identity, "A", dict(a="A", b="A")


def duplicate_output_list_node():
    return identity, "A", ["A", "A"]


@pytest.mark.parametrize(
    "func, expected",
    [
        (bad_input_type_node, r"`inputs` type must be one of "),
        (bad_output_type_node, r"`outputs` type must be one of "),
        (bad_function_type_node, r"first argument must be a function"),
        (no_input_or_output_node, r"it must have some `inputs` or `outputs`"),
        (
            input_same_as_output_node,
            r"A node cannot have the same inputs and outputs: {\'A\'}",
        ),
        (
            duplicate_output_dict_node,
            r"Failed to create node identity"
            r"\(\[A\]\) -> \[A,A\] due to "
            r"duplicate output\(s\) {\'A\'}.",
        ),
        (
            duplicate_output_list_node,
            r"Failed to create node identity"
            r"\(\[A\]\) -> \[A,A\] due to "
            r"duplicate output\(s\) {\'A\'}.",
        ),
    ],
)
def test_bad_node(func, expected):
    with pytest.raises(ValueError, match=expected):
        node(*func())


def inconsistent_input_size():
    return identity, ["A", "B"], "C"


def inconsistent_input_args():
    def dummy_func_args(*args):
        return "".join([*args])  # pragma: no cover

    return dummy_func_args, {"a": "A"}, "B"


def inconsistent_input_kwargs():
    def dummy_func_args(**kwargs):
        return list(kwargs.values())  # pragma: no cover

    return dummy_func_args, "A", "B"


@pytest.mark.parametrize(
    "func, expected",
    [
        (
            inconsistent_input_size,
            r"Inputs of function expected \[\'input1\'\], but got \[\'A\', \'B\'\]",
        ),
        (
            inconsistent_input_args,
            r"Inputs of function expected \[\'args\'\], but got {\'a\': \'A\'}",
        ),
        (
            inconsistent_input_kwargs,
            r"Inputs of function expected \[\'kwargs\'\], but got A",
        ),
    ],
)
def test_bad_input(func, expected):
    with pytest.raises(TypeError, match=expected):
        node(*func())


def apply_f(func: Callable) -> Callable:
    @wraps(func)
    def with_f(*args, **kwargs):
        return func(*["f(%s)" % a for a in args], **kwargs)

    return with_f


def apply_g(func: Callable) -> Callable:
    @wraps(func)
    def with_g(*args, **kwargs):
        return func(*["g(%s)" % a for a in args], **kwargs)

    return with_g


def apply_h(func: Callable) -> Callable:
    @wraps(func)
    def with_h(*args, **kwargs):
        return func(*["h(%s)" % a for a in args], **kwargs)

    return with_h


def apply_ij(func: Callable) -> Callable:
    @wraps(func)
    def with_ij(*args, **kwargs):
        return func(*["ij(%s)" % a for a in args], **kwargs)

    return with_ij


@apply_f
def decorated_identity(value):
    return value


class TestTagDecorator:
    def test_apply_decorators(self):
        old_node = node(apply_g(decorated_identity), "input", "output", name="node")
        new_node = old_node.decorate(apply_h, apply_ij)
        result = new_node.run(dict(input=1))

        assert old_node.name == new_node.name
        assert "output" in result
        assert result["output"] == "f(g(ij(h(1))))"

    def test_tag_nodes(self):
        tagged_node = node(identity, "input", "output", tags=["hello"]).tag(["world"])
        assert "hello" in tagged_node.tags
        assert "world" in tagged_node.tags
        assert len(tagged_node.tags) == 2

    def test_tag_nodes_single_tag(self):
        tagged_node = node(identity, "input", "output", tags="hello").tag("world")
        assert "hello" in tagged_node.tags
        assert "world" in tagged_node.tags
        assert len(tagged_node.tags) == 2

    def test_tag_and_decorate(self):
        tagged_node = node(identity, "input", "output", tags=["hello"])
        tagged_node = tagged_node.decorate(apply_f)
        tagged_node = tagged_node.tag(["world"])
        assert "hello" in tagged_node.tags
        assert "world" in tagged_node.tags
        assert tagged_node.run(dict(input=1))["output"] == "f(1)"


class TestNames:
    def test_named(self):
        n = node(identity, ["in"], ["out"], name="name")
        assert str(n) == "name: identity([in]) -> [out]"
        assert n.name == "name"
        assert n.short_name == "name"

    def test_function(self):
        n = node(identity, ["in"], ["out"])
        assert str(n) == "identity([in]) -> [out]"
        assert n.name == "identity([in]) -> [out]"
        assert n.short_name == "Identity"

    def test_lambda(self):
        n = node(lambda a: a, ["in"], ["out"])
        assert str(n) == "<lambda>([in]) -> [out]"
        assert n.name == "<lambda>([in]) -> [out]"
        assert n.short_name == "<Lambda>"

    def test_partial(self):
        n = node(partial(identity), ["in"], ["out"])
        assert str(n) == "<partial>([in]) -> [out]"
        assert n.name == "<partial>([in]) -> [out]"
        assert n.short_name == "<Partial>"

    def test_updated_partial(self):
        n = node(update_wrapper(partial(identity), identity), ["in"], ["out"])
        assert str(n) == "identity([in]) -> [out]"
        assert n.name == "identity([in]) -> [out]"
        assert n.short_name == "Identity"
