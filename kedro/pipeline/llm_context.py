from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import NamedTuple

from .node import Node, node


class _ToolConfig(NamedTuple):
    func: Callable[..., object]
    inputs: Sequence[str]


def tool(func: Callable[..., object], *inputs: str) -> _ToolConfig:
    """Builder function for a tool (name derived from built object)."""
    return _ToolConfig(func=func, inputs=list(inputs))


@dataclass
class LLMContext:
    context_id: str
    llm: object
    prompts: dict[str, object] = field(default_factory=dict)
    tools: dict[str, object] = field(default_factory=dict)


def _get_tool_name(obj: object) -> str:
    """Return a readable name for a tool object."""
    if hasattr(obj, "__name__"):
        return obj.__name__
    if hasattr(obj, "name"):
        return obj.name
    if hasattr(obj, "__class__"):
        return obj.__class__.__name__
    return str(obj)


def llm_context_node(
    *,
    outputs: str,
    llm: str,
    prompts: list[str],
    tools: list[_ToolConfig] | None = None,
    name: str = "llm_context_node",
) -> Node:
    """
    1. Kedro validates all datasets (llm, prompts, db_engine, docs, etc.).
    2. Tools stay as plain Python functions, passed at node construction.
    3. We build them inside the wrapper at execution time
    """
    inputs = {"llm": llm}

    # Add prompts as validated inputs
    for p in prompts:
        inputs[p] = p

    # Add tool inputs (datasets + params)
    if tools:
        for t in tools:
            for inp in t.inputs:
                inputs[inp] = inp

    def construct_context(llm, **kwargs):
        # Collect prompts
        prompts_dict = {k: v for k, v in kwargs.items() if "prompt" in k}

        # Build tools
        built_tools = {}
        if tools:
            for t in tools:
                tool_inputs = {
                    inp.replace("params:", ""): kwargs[inp] for inp in t.inputs
                }
                built_tool = t.func(**tool_inputs)
                built_tools[_get_tool_name(built_tool)] = built_tool

        return LLMContext(
            context_id=name,
            llm=llm,
            prompts=prompts_dict,
            tools=built_tools,
        )

    return node(func=construct_context, inputs=inputs, outputs=outputs, name=name)
