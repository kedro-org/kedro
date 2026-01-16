import re
from collections.abc import Callable
from functools import partial, update_wrapper, wraps

import pytest

from kedro.pipeline import node
from kedro.pipeline.preview_contract import (
    CustomPreview,
    ImagePreview,
    JsonPreview,
    MermaidPreview,
    PlotlyPreview,
    TablePreview,
    TextPreview,
)
from kedro.utils import KedroExperimentalWarning
from tests.test_utils import biconcat, constant_output, identity, triconcat


@pytest.fixture
def simple_tuple_node_list():
    return [
        (identity, "A", "B"),
        (biconcat, ["A", "B"], "C"),
        (identity, "C", ["D", "E"]),
        (biconcat, ["H", "I"], ["J", "K"]),
        (identity, "J", {"result": "K"}),
        (biconcat, ["J", "K"], {"result": "L"}),
        (identity, {"input1": "J"}, "L"),
        (identity, {"input1": "J"}, ["L", "M"]),
        (identity, {"input1": "J"}, {"result": "K"}),
        (constant_output, None, "M"),
        (biconcat, ["N", "O"], None),
        (lambda x: None, "F", "G"),
        (lambda x: ("a", "b"), "G", ["X", "Y"]),
    ]


class TestValidNode:
    def test_valid(self, simple_tuple_node_list):
        nodes = [node(*tup) for tup in simple_tuple_node_list]
        assert len(nodes) == len(simple_tuple_node_list)

    def test_get_node_func(self):
        test_node = node(identity, "A", "B")
        assert test_node.func is identity

    def test_set_node_func(self):
        test_node = node(identity, "A", "B")
        test_node.func = decorated_identity
        assert test_node.func is decorated_identity

    def test_labelled(self):
        assert "labeled_node: <lambda>([input1]) -> [output1]" in str(
            node(lambda x: None, "input1", "output1", name="labeled_node")
        )

    def test_call(self):
        dummy_node = node(
            biconcat, inputs=["input1", "input2"], outputs="output", name="myname"
        )
        actual = dummy_node(input1="in1", input2="in2")
        expected = dummy_node.run({"input1": "in1", "input2": "in2"})
        assert actual == expected

    def test_call_with_non_keyword_arguments(self):
        dummy_node = node(
            biconcat, inputs=["input1", "input2"], outputs="output", name="myname"
        )
        pattern = r"__call__\(\) takes 1 positional argument but 2 were given"
        with pytest.raises(TypeError, match=pattern):
            dummy_node("in1", input2="in2")

    def test_run_with_duplicate_inputs_list(self):
        dummy_node = node(func=biconcat, inputs=["input1", "input1"], outputs="output")
        actual = dummy_node.run({"input1": "in1"})
        assert actual == {"output": "in1in1"}

    def test_run_with_duplicate_inputs_dict(self):
        dummy_node = node(
            func=biconcat, inputs={"input1": "in1", "input2": "in1"}, outputs="output"
        )
        actual = dummy_node.run({"in1": "hello"})
        assert actual == {"output": "hellohello"}

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

    @pytest.mark.parametrize(
        "confirms_arg,expected",
        [
            (None, []),
            ([], []),
            ("foo", ["foo"]),
            (["foo"], ["foo"]),
            (["foo", "bar"], ["foo", "bar"]),
        ],
    )
    def test_confirms(self, confirms_arg, expected):
        dummy_node = node(identity, "input", None, confirms=confirms_arg)
        assert dummy_node.confirms == expected


class TestNodeComparisons:
    def test_node_equals(self):
        first = node(identity, "input1", "output1", name="a_node")
        second = node(identity, "input1", "output1", name="a_node")
        assert first == second
        assert first is not second

    def test_node_less_than(self):
        first = node(identity, "input1", "output1", name="A")
        second = node(identity, "input1", "output1", name="B")
        assert first < second
        assert first is not second

    def test_node_invalid_equals(self):
        n = node(identity, "input1", "output1", name="a_node")
        assert n != "hello"

    def test_node_invalid_less_than(self):
        n = node(identity, "input1", "output1", name="a_node")
        pattern = "'<' not supported between instances of 'Node' and 'str'"

        with pytest.raises(TypeError, match=pattern):
            n < "hello"

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
    return biconcat, ["A", "B"], {"a": "A"}


def transcoded_input_same_as_output_node():
    return identity, "A@excel", {"a": "A@csv"}


def duplicate_output_dict_node():
    return identity, "A", {"a": "A", "b": "A"}


def duplicate_output_list_node():
    return identity, "A", ["A", "A"]


def bad_input_variable_name():
    return lambda x: None, {"a": 1, "b": "B"}, {"a": "A", "b": "B"}


def bad_output_variable_name():
    return lambda x: None, {"a": "A", "b": "B"}, {"a": "A", "b": 2}


@pytest.mark.parametrize(
    "func, expected",
    [
        (bad_input_type_node, r"'inputs' type must be one of "),
        (bad_output_type_node, r"'outputs' type must be one of "),
        (bad_function_type_node, r"first argument must be a function"),
        (no_input_or_output_node, r"it must have some 'inputs' or 'outputs'"),
        (
            input_same_as_output_node,
            r"A node cannot have the same inputs and outputs even if they are transcoded: {\'A\'}",
        ),
        (
            transcoded_input_same_as_output_node,
            r"A node cannot have the same inputs and outputs even if they are transcoded: {\'A\'}",
        ),
        (
            duplicate_output_dict_node,
            r"Failed to create node identity"
            r"\(\[A\]\) -> \[A;A\] due to "
            r"duplicate output\(s\) {\'A\'}.",
        ),
        (
            duplicate_output_list_node,
            r"Failed to create node identity"
            r"\(\[A\]\) -> \[A;A\] due to "
            r"duplicate output\(s\) {\'A\'}.",
        ),
        (bad_input_variable_name, "names of variables used as inputs to the function "),
        (
            bad_output_variable_name,
            "names of variables used as outputs of the function ",
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


lambda_identity = lambda input1: input1  # noqa: E731


def lambda_inconsistent_input_size():
    return lambda_identity, ["A", "B"], "C"


partial_identity = partial(identity)


def partial_inconsistent_input_size():
    return partial_identity, ["A", "B"], "C"


@pytest.mark.parametrize(
    "func, expected",
    [
        (
            inconsistent_input_size,
            r"Inputs of 'identity' function expected \[\'input1\'\], but got \[\'A\', \'B\'\]",
        ),
        (
            inconsistent_input_args,
            r"Inputs of 'dummy_func_args' function expected \[\'args\'\], but got {\'a\': \'A\'}",
        ),
        (
            inconsistent_input_kwargs,
            r"Inputs of 'dummy_func_args' function expected \[\'kwargs\'\], but got A",
        ),
        (
            lambda_inconsistent_input_size,
            r"Inputs of '<lambda>' function expected \[\'input1\'\], but got \[\'A\', \'B\'\]",
        ),
        (
            partial_inconsistent_input_size,
            r"Inputs of '<partial>' function expected \[\'input1\'\], but got \[\'A\', \'B\'\]",
        ),
    ],
)
def test_bad_input(func, expected):
    with pytest.raises(TypeError, match=expected):
        node(*func())


def apply_f(func: Callable) -> Callable:
    @wraps(func)
    def with_f(*args, **kwargs):
        return func(*(f"f({a})" for a in args), **kwargs)  # pragma: no cover

    return with_f


@apply_f
def decorated_identity(value):
    return value  # pragma: no cover


class TestTag:
    def test_tag_nodes(self):
        tagged_node = node(identity, "input", "output", tags=["hello"]).tag(["world"])
        assert "hello" in tagged_node.tags
        assert "world" in tagged_node.tags
        assert len(tagged_node.tags) == 2

    def test_tag_nodes_single_tag(self):
        tagged_node = node(identity, "input", "output", tags="hello").tag("world")
        assert "hello" in tagged_node.tags
        assert "world" in tagged_node.tags

    @pytest.mark.parametrize("bad_tag", ["tag,with,comma", "tag with space"])
    def test_invalid_tag(self, bad_tag):
        pattern = (
            f"'{bad_tag}' is not a valid node tag. It must contain only "
            f"letters, digits, hyphens, underscores and/or fullstops."
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            node(identity, ["in"], ["out"], tags=bad_tag)


class TestNames:
    def test_named(self):
        n = node(identity, ["in"], ["out"], name="name")
        assert str(n) == "name: identity([in]) -> [out]"
        assert n.name == "name"
        assert n.short_name == "name"

    @pytest.mark.parametrize("bad_name", ["name,with,comma", "name with space"])
    def test_invalid_name(self, bad_name):
        pattern = (
            f"'{bad_name}' is not a valid node name. "
            f"It must contain only letters, digits, hyphens, "
            f"underscores and/or fullstops."
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            node(identity, ["in"], ["out"], name=bad_name)

    def test_namespaced(self):
        n = node(identity, ["in"], ["out"], namespace="namespace")
        assert str(n) == "identity([in]) -> [out]"
        assert re.match(r"^namespace\.identity__[0-9a-f]{8}$", n.name)
        assert n.short_name == "Identity"

    def test_namespace_prefixes(self):
        n = node(identity, ["in"], ["out"], namespace="a.b.c.d.e.f")
        assert n.namespace_prefixes == [
            "a",
            "a.b",
            "a.b.c",
            "a.b.c.d",
            "a.b.c.d.e",
            "a.b.c.d.e.f",
        ]

    def test_named_and_namespaced(self):
        n = node(identity, ["in"], ["out"], name="name", namespace="namespace")
        assert str(n) == "name: identity([in]) -> [out]"
        assert n.name == "namespace.name"
        assert n.short_name == "name"

    def test_function(self):
        n = node(identity, ["in"], ["out"])
        assert str(n) == "identity([in]) -> [out]"
        assert re.match(r"^identity__[0-9a-f]{8}$", n.name)
        assert n.short_name == "Identity"

    def test_lambda(self):
        n = node(lambda a: a, ["in"], ["out"])
        assert str(n) == "<lambda>([in]) -> [out]"
        assert re.match(r"^<lambda>__[0-9a-f]{8}$", n.name)
        assert n.short_name == "<Lambda>"

    def test_partial(self):
        n = node(partial(identity), ["in"], ["out"])
        assert str(n) == "<partial>([in]) -> [out]"
        assert re.match(r"^partial\(identity\)__[0-9a-f]{8}$", n.name)
        assert n.short_name == "<Partial>"

    def test_updated_partial(self):
        n = node(update_wrapper(partial(identity), identity), ["in"], ["out"])
        assert str(n) == "identity([in]) -> [out]"
        assert re.match(r"^partial\(identity\)__[0-9a-f]{8}$", n.name)
        assert n.short_name == "Identity"

    def test_updated_partial_dict_inputs(self):
        n = node(
            update_wrapper(partial(biconcat, input1=["in1"]), biconcat),
            {"input2": "in2"},
            ["out"],
        )
        assert str(n) == "biconcat([in2]) -> [out]"
        assert re.match(r"^partial\(biconcat\)__[0-9a-f]{8}$", n.name)
        assert n.short_name == "Biconcat"


class TestNodeInputOutputNameValidation:
    @staticmethod
    def dummy_function(input_data):
        return input_data

    def test_valid_namespaced_inputs_and_outputs(self):
        """Test that valid namespaced inputs and outputs are accepted."""
        n = node(
            func=self.dummy_function,
            inputs="namespace.input_dataset",
            outputs="namespace.output_dataset",
            namespace="namespace",
        )
        assert n.inputs == ["namespace.input_dataset"]
        assert n.outputs == ["namespace.output_dataset"]

    def test_invalid_namespaced_inputs(self):
        """Test that inputs with mismatched namespaces raise a ValueError."""
        with pytest.warns(
            UserWarning,
            match="Dataset name 'wrong_namespace.input_dataset' contains '.' characters",
        ):
            node(
                func=self.dummy_function,
                inputs="wrong_namespace.input_dataset",
                outputs="namespace.output_dataset",
                namespace="namespace",
            )

    def test_invalid_namespaced_outputs(self):
        """Test that outputs with mismatched namespaces raise a ValueError."""
        with pytest.warns(
            UserWarning,
            match="Dataset name 'wrong_namespace.output_dataset' contains '.' characters",
        ):
            node(
                func=self.dummy_function,
                inputs="namespace.input_dataset",
                outputs="wrong_namespace.output_dataset",
                namespace="namespace",
            )

    def test_valid_params_prefixed_inputs(self):
        """Test that params-prefixed inputs are accepted."""
        n = node(
            func=self.dummy_function,
            inputs="params:example.param",
            outputs="output_dataset",
        )
        assert n.inputs == ["params:example.param"]
        assert n.outputs == ["output_dataset"]

    def test_invalid_inputs_with_dot_no_namespace(self):
        """Test that inputs with '.' but no namespace raise a ValueError."""
        with pytest.warns(
            UserWarning, match="Dataset name 'input.dataset' contains '.' characters"
        ):
            node(
                func=self.dummy_function,
                inputs="input.dataset",
                outputs="output_dataset",
            )

    def test_invalid_outputs_with_dot_no_namespace(self):
        """Test that outputs with '.' but no namespace raise a ValueError."""
        with pytest.warns(
            UserWarning, match="Dataset name 'output.dataset' contains '.' characters"
        ):
            node(
                func=self.dummy_function,
                inputs="input_dataset",
                outputs="output.dataset",
            )

    def test_valid_multi_level_namespace(self):
        """Test that multi-level namespaces are accepted."""
        n = node(
            func=self.dummy_function,
            inputs="namespace.subnamespace.input_dataset",
            outputs="namespace.subnamespace.output_dataset",
            namespace="namespace.subnamespace",
        )
        assert n.inputs == ["namespace.subnamespace.input_dataset"]
        assert n.outputs == ["namespace.subnamespace.output_dataset"]

    def test_dataset_namespace_matches_pipeline_namespace(self):
        """Test that node level namespace specification doesn't throw the error."""
        n = node(
            func=self.dummy_function,
            inputs="namespace.input_dataset",
            outputs="namespace.output_dataset",
            namespace="namespace.other",
        )
        assert n.inputs == ["namespace.input_dataset"]
        assert n.outputs == ["namespace.output_dataset"]

    def test_mismatched_namespace(self):
        """Test that mismatched namespaces in inputs and outputs raise a UserWarning."""
        with pytest.warns(
            UserWarning,
            match="Dataset name 'other_namespace.output_dataset' contains '.' characters",
        ):
            node(
                func=self.dummy_function,
                inputs="namespace.input_dataset",
                outputs="other_namespace.output_dataset",
                namespace="namespace",
            )


class TestNodePreviewPayload:
    def test_json_preview_with_dict(self):
        payload = JsonPreview(content={"key": "value"})
        assert payload.kind == "json"
        assert payload.content == {"key": "value"}
        assert payload.meta is None

    def test_json_preview_with_list(self):
        payload = JsonPreview(content=[1, 2, 3])
        assert payload.kind == "json"
        assert payload.content == [1, 2, 3]
        assert payload.meta is None

    def test_json_preview_with_meta(self):
        payload = JsonPreview(content={"key": "value"}, meta={"format": "pretty"})
        assert payload.kind == "json"
        assert payload.content == {"key": "value"}
        assert payload.meta == {"format": "pretty"}

    def test_text_preview(self):
        payload = TextPreview(content="test content")
        assert payload.kind == "text"
        assert payload.content == "test content"

    def test_mermaid_preview(self):
        payload = MermaidPreview(content="graph LR\n A --> B")
        assert payload.kind == "mermaid"
        assert payload.content == "graph LR\n A --> B"

    def test_table_preview(self):
        payload = TablePreview(
            content=[{"col1": "a", "col2": 1}, {"col1": "b", "col2": 2}],
        )
        assert payload.kind == "table"
        assert payload.content == [
            {"col1": "a", "col2": 1},
            {"col1": "b", "col2": 2},
        ]

    def test_plotly_preview(self):
        payload = PlotlyPreview(content={"data": [], "layout": {}})
        assert payload.kind == "plotly"
        assert payload.content == {"data": [], "layout": {}}

    def test_image_preview_with_url(self):
        payload = ImagePreview(content="https://example.com/image.png")
        assert payload.kind == "image"
        assert payload.content == "https://example.com/image.png"

    def test_image_preview_with_data_uri(self):
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        payload = ImagePreview(content=data_uri)
        assert payload.kind == "image"
        assert payload.content == data_uri

    def test_custom_preview(self):
        payload = CustomPreview(renderer_key="my_renderer", content={"custom": "data"})
        assert payload.kind == "custom"
        assert payload.renderer_key == "my_renderer"
        assert payload.content == {"custom": "data"}

    def test_invalid_content_type_for_text(self):
        with pytest.raises(TypeError, match="TextPreview.content must be str"):
            TextPreview(content={"invalid": "type"})

    def test_invalid_content_type_for_json(self):
        with pytest.raises(TypeError, match="value is not JSON-serializable"):
            JsonPreview(content=object())

    def test_invalid_content_type_for_table(self):
        with pytest.raises(TypeError, match="TablePreview.content must be list"):
            TablePreview(content={"invalid": "type"})

    def test_table_content_with_non_dict_rows(self):
        with pytest.raises(
            TypeError, match="TablePreview.content\\[\\d+\\] must be dict"
        ):
            TablePreview(content=["not", "dicts"])

    def test_invalid_content_type_for_plotly(self):
        with pytest.raises(TypeError, match="PlotlyPreview.content must be dict"):
            PlotlyPreview(content="should be dict")

    def test_invalid_custom_preview_missing_renderer_key(self):
        with pytest.raises(
            TypeError, match="CustomPreview.renderer_key must be a non-empty str"
        ):
            CustomPreview(renderer_key="", content={"data": "value"})


class TestNodePreviewFunction:
    @pytest.fixture(autouse=True)
    def reset_preview_warning_flag(self):
        """Reset the preview_fn warning flag before and after each test."""
        from kedro.pipeline.node import Node

        # Remove the flag before the test
        if hasattr(Node, "__preview_fn_warned__"):
            delattr(Node, "__preview_fn_warned__")

        yield

        # Clean up after the test
        if hasattr(Node, "__preview_fn_warned__"):
            delattr(Node, "__preview_fn_warned__")

    def test_node_with_preview_fn_emits_warning_only_once(self):
        """Test that the preview_fn warning is only emitted once per session."""

        def test_json_preview():
            return JsonPreview(content={"test": "data"})

        def another_preview():
            return TextPreview(content="another")

        import warnings

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Create first node - should warn
            node1 = node(identity, "input1", "output1", preview_fn=test_json_preview)
            warnings_after_first = [
                w
                for w in warning_list
                if issubclass(w.category, KedroExperimentalWarning)
            ]
            assert len(warnings_after_first) == 1
            assert "preview_fn" in str(warnings_after_first[0].message)

            # Create second node - should NOT warn (same session)
            node2 = node(identity, "input2", "output2", preview_fn=another_preview)
            warnings_after_second = [
                w
                for w in warning_list
                if issubclass(w.category, KedroExperimentalWarning)
            ]
            assert len(warnings_after_second) == 1  # No additional warnings

            # Create third node - should NOT warn (same session)
            node3 = node(identity, "input3", "output3", preview_fn=test_json_preview)
            warnings_after_third = [
                w
                for w in warning_list
                if issubclass(w.category, KedroExperimentalWarning)
            ]
            assert len(warnings_after_third) == 1  # Still only one warning total

        assert node1._preview_fn is test_json_preview
        assert node2._preview_fn is another_preview
        assert node3._preview_fn is test_json_preview

    def test_node_without_preview_fn_no_warning(self):
        import warnings

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            node(identity, "input", "output")
        experimental_warnings = [
            w for w in warning_list if issubclass(w.category, KedroExperimentalWarning)
        ]
        assert len(experimental_warnings) == 0

    def test_preview_fn_not_callable_raises_error(self):
        pattern = r"preview_fn must be a function, not 'str'"
        with pytest.raises(ValueError, match=pattern):
            node(identity, "input", "output", preview_fn="not a function")

    def test_preview_returns_none_when_no_preview_fn(self):
        n = node(identity, "input", "output")
        result = n.preview()
        assert result is None

    def test_preview_executes_preview_fn(self):
        def test_json_preview():
            return JsonPreview(content={"key": "value"})

        with pytest.warns(KedroExperimentalWarning):
            n = node(identity, "input", "output", preview_fn=test_json_preview)

        result = n.preview()

        assert isinstance(result, JsonPreview)
        assert result.kind == "json"
        assert result.content == {"key": "value"}

    def test_preview_fn(self):
        def preview_fn():
            return TablePreview(content=[{"col": "value"}])

        with pytest.warns(KedroExperimentalWarning):
            n = node(identity, "input", "output", preview_fn=preview_fn)

        result = n.preview()

        assert isinstance(result, TablePreview)
        assert result.kind == "table"
        assert result.content == [{"col": "value"}]

    def test_preview_validates_return_type(self):
        def bad_preview_fn():
            return "not a PreviewPayload"

        with pytest.warns(KedroExperimentalWarning):
            n = node(identity, "input", "output", preview_fn=bad_preview_fn)

        pattern = r"preview_fn must return one of the valid preview types.*but got 'str' instead"
        with pytest.raises(ValueError, match=pattern):
            n.preview()

    def test_preview_validates_return_type_dict(self):
        def bad_preview_fn():
            return {"kind": "json", "content": "test"}

        with pytest.warns(KedroExperimentalWarning):
            n = node(identity, "input", "output", preview_fn=bad_preview_fn)

        pattern = r"preview_fn must return one of the valid preview types.*but got 'dict' instead"
        with pytest.raises(ValueError, match=pattern):
            n.preview()

    def test_preview_fn_preserved_in_copy(self):
        def preview_fn():
            return TextPreview(content="preview")

        with pytest.warns(KedroExperimentalWarning):
            original = node(identity, "input", "output", preview_fn=preview_fn)

        copied = original._copy(name="new_name")
        assert copied._preview_fn is preview_fn

    def test_preview_fn_can_be_overwritten_in_copy(self):
        def preview_fn1():
            return TextPreview(content="preview1")

        def preview_fn2():
            return JsonPreview(content={"data": "preview2"})

        with pytest.warns(KedroExperimentalWarning):
            original = node(identity, "input", "output", preview_fn=preview_fn1)

        copied = original._copy(preview_fn=preview_fn2)
        assert original._preview_fn is preview_fn1
        assert copied._preview_fn is preview_fn2
