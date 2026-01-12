import pytest

from kedro.pipeline.llm_context import (
    LLMContext,
    _get_tool_name,
    _normalize_outputs,
    llm_context_node,
    tool,
)


class DummyTool:
    """Simple tool object used for testing."""

    def __init__(self, value):
        self.value = value


def build_dummy_tool(tool_input):
    """Tool builder returning a DummyTool."""
    return DummyTool(tool_input)


def test_tool_builder_stores_func_and_inputs():
    """tool() should capture the builder function and its declared inputs."""
    cfg = tool(build_dummy_tool, "some_input", "params:foo")

    assert cfg.func is build_dummy_tool
    assert list(cfg.inputs) == ["some_input", "params:foo"]


def test_llm_context_node_declares_all_inputs():
    """All LLM, prompt, and tool inputs should be declared on the node."""
    node_obj = llm_context_node(
        outputs="context",
        llm="llm",
        prompts=["prompt_a", "prompt_b"],
        tools=[tool(build_dummy_tool, "tool_input")],
        name="ctx_node",
    )

    assert set(node_obj.inputs) == {
        "llm",
        "prompt_a",
        "prompt_b",
        "tool_input",
    }


def test_llm_context_node_builds_context_without_tools():
    """Node execution should build LLMContext with prompts and no tools."""
    node_obj = llm_context_node(
        outputs="context",
        llm="llm",
        prompts=["prompt"],
    )

    context = node_obj.func(
        llm="dummy_llm",
        prompt="hello",
    )

    assert isinstance(context, LLMContext)
    assert context.llm == "dummy_llm"
    assert context.prompts == {"prompt": "hello"}
    assert context.tools == {}


def test_llm_context_node_builds_tools_with_inputs():
    """Tools should be instantiated at runtime using declared inputs."""
    node_obj = llm_context_node(
        outputs="context",
        llm="llm",
        prompts=["prompt"],
        tools=[tool(build_dummy_tool, "tool_input")],
    )

    context = node_obj.func(
        llm="dummy_llm",
        prompt="hello",
        tool_input=42,
    )

    assert "DummyTool" in context.tools
    assert isinstance(context.tools["DummyTool"], DummyTool)
    assert context.tools["DummyTool"].value == 42


def test_context_id_uses_node_name_when_provided():
    """context_id should match node name when name is provided."""
    node_obj = llm_context_node(
        outputs="context",
        llm="llm",
        prompts=[],
        name="my_context",
    )

    context = node_obj.func(llm="dummy_llm")

    assert context.context_id == "my_context"


@pytest.mark.parametrize(
    "outputs,expected_suffix",
    [
        ("my_output", "my_output"),
        (["out_a", "out_b"], "out_a__out_b"),
        ({"a": "out_x", "b": "out_y"}, "out_x__out_y"),
    ],
)
def test_context_id_falls_back_to_outputs_when_name_missing(outputs, expected_suffix):
    """context_id should be derived from outputs when name is None.

    This verifies that string, list, and dict outputs are normalized
    consistently and used to generate a stable context identifier.
    """
    node_obj = llm_context_node(
        outputs=outputs,
        llm="llm",
        prompts=[],
        name=None,
    )

    context = node_obj.func(llm="dummy_llm")

    assert context.context_id == f"llm_context_node__{expected_suffix}"


@pytest.mark.parametrize(
    "outputs,expected",
    [
        ("out", "out"),
        (["a", "b"], "a__b"),
        ({"x": "y"}, "y"),
        ((1, 2), "(1, 2)"),  # fallback branch
    ],
)
def test_normalize_outputs_all_branches(outputs, expected):
    """_normalize_outputs should return a deterministic string for all inputs.

    This test covers all supported output shapes plus the fallback branch
    used for unexpected types.
    """
    assert _normalize_outputs(outputs) == expected


def test_only_declared_prompts_are_collected():
    """Only prompts explicitly listed should appear in the context."""
    node_obj = llm_context_node(
        outputs="context",
        llm="llm",
        prompts=["prompt_a"],
    )

    context = node_obj.func(
        llm="dummy_llm",
        prompt_a="included",
        extra="ignored",
    )

    assert context.prompts == {"prompt_a": "included"}


def func_example():
    pass


class ClassWithNameAttr:
    name = "custom_name"


class DummyClass:
    pass


@pytest.mark.parametrize(
    "obj,expected_name",
    [
        (func_example, "func_example"),
        (ClassWithNameAttr(), "custom_name"),
        (DummyClass(), "DummyClass"),
        (object(), "object"),
    ],
)
def test_get_tool_name_all_branches(obj, expected_name):
    """_get_tool_name should derive a stable, human-friendly tool name."""
    assert _get_tool_name(obj) == expected_name
