from collections.abc import Callable
from dataclasses import dataclass, field

from .node import Node, node


@dataclass
class LLMContext:
    context_id: str
    llm: object
    prompts: dict[str, object] = field(default_factory=dict)
    tools: dict[str, Callable] = field(default_factory=dict)


def _get_tool_name(func: Callable):
    """Return a readable tool name from callable or tool-like object."""
    if hasattr(func, "__name__"):
        return func.__name__
    if hasattr(func, "name"):
        return func.name
    if hasattr(func, "__class__"):
        return func.__class__.__name__
    return str(func)


def llm_context_node(
    *,
    outputs,
    llm,
    prompts,
    tools=None,
    name="llm_context_node",
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
        for tool in tools:
            for inp in tool.get("inputs", []):
                inputs[inp] = inp

    def construct_context(llm, **kwargs):
        # Collect prompts
        prompts_dict = {k: v for k, v in kwargs.items() if "prompt" in k}

        # Collect tools
        built_tools = {}
        if tools:
            for tool in tools:
                tool_inputs = {}
                for inp in tool.get("inputs", []):
                    val = kwargs[inp]
                    clean_key = inp.replace("params:", "")
                    tool_inputs[clean_key] = val

                built_tool = tool["func"](**tool_inputs)
                built_tools[_get_tool_name(built_tool)] = built_tool

        return LLMContext(
            context_id=name, llm=llm, prompts=prompts_dict, tools=built_tools
        )

    return node(func=construct_context, inputs=inputs, outputs=outputs, name=name)
