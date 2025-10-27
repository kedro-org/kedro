from dataclasses import dataclass, field
from typing import Callable

from .node import Node, node


@dataclass
class AgentContext:
    agent_id: str
    llm: object
    prompts: dict[str, object] = field(default_factory=dict)
    tools: dict[str, Callable] = field(default_factory=dict)


def get_tool_name(func: Callable):
    """Return a readable tool name from callable or tool-like object."""
    if hasattr(func, "__name__"):
        return func.__name__
    if hasattr(func, "name"):
        return func.name
    if hasattr(func, "__class__"):
        return func.__class__.__name__
    return str(func)


def agent_context_node(  # noqa: PLR0913
    *,
    outputs,
    llm,
    prompts,
    tools=None,
    name="agent_context_node",
    agent_id="default_agent",
) -> Node:
    """
    1. Kedro validates all datasets (llm, prompts, db_engine, docs, etc.).
    2. Tools stay as plain Python functions, passed at node construction.
    3. We build them inside the wrapper at execution time
    """
    inputs = {"llm": llm}
    for p in prompts:
        inputs[p] = p
    if tools:
        for tool in tools:
            for inp in tool.get("inputs", []):
                inputs[inp] = inp

    def construct_context(llm, **kwargs):
        prompts = {k: v for k, v in kwargs.items() if "prompt" in k}
        built_tools = {}
        if tools:
            for tool in tools:
                tool_inputs = {inp: kwargs[inp] for inp in tool.get("inputs", [])}
                built_tool = tool["func"](**tool_inputs)
                built_tools[get_tool_name(built_tool)] = built_tool
        return AgentContext(
            agent_id=agent_id, llm=llm, prompts=prompts, tools=built_tools
        )

    return node(func=construct_context, inputs=inputs, outputs=outputs, name=name)
