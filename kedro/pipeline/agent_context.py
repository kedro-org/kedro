from dataclasses import dataclass, field
from typing import Callable

from .node import Node, node


@dataclass
class AgentContext:
    agent_id: str
    llm: object
    prompts: dict[str, object] = field(default_factory=dict)
    tools: dict[str, Callable] = field(default_factory=dict)


def agent_context_node(
    *, outputs, llm, prompts, tools=None, name="agent_context_node"
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
                built_tools[tool["func"].__name__] = tool["func"](**tool_inputs)
        return AgentContext(
            agent_id="default_agent", llm=llm, prompts=prompts, tools=built_tools
        )

    return node(func=construct_context, inputs=inputs, outputs=outputs, name=name)
