"""
Experimental utilities for constructing an ``LLMContext`` inside a Kedro pipeline.

This module provides:

- A `tool()` builder for declaring tool constructors and their Kedro inputs.
- An `llm_context_node()` helper that creates a Kedro node which assembles:
  - an LLM instance,
  - prompt datasets,
  - dynamically built tool objects.

All datasets required by the context (LLM, prompts, tool inputs) are validated
and loaded by Kedro before the node runs. Tools are instantiated at execution
time and automatically assigned readable names based on the returned objects.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple, TypeVar

from ..utils import experimental
from .node import Node, node

T = TypeVar("T")


class _ToolConfig(NamedTuple):
    """Configuration for a tool builder.

    This stores:
    - the builder function (`func`) that constructs a tool object
    - the Kedro inputs (`inputs`) required by that builder
    """

    func: Callable[..., object]
    inputs: Sequence[str]


@experimental
def tool(func: Callable[..., T], *inputs: str) -> _ToolConfig:
    """Create a `_ToolConfig` definition for a tool builder.

    Args:
        func: A callable that constructs and returns a tool object.
            Its name will *not* define the tool name; the name is derived from
            the returned object when the tool is instantiated.
        *inputs: Kedro dataset names (including params:* entries) required by `func`.

    Returns:
        A configuration object used by ``llm_context_node`` to construct tools
        at execution time
    """
    return _ToolConfig(func=func, inputs=list(inputs))


@experimental
@dataclass
class LLMContext:
    """Runtime context passed to an LLM execution step.

    Args:
        context_id: Logical identifier for the context (usually the node name).
        llm: The LLM or LLM wrapper loaded by Kedro.
        prompts: A mapping of prompt dataset names → prompt content.
        tools: A mapping of tool names to instantiated tool objects.
            Tool names are automatically derived from each built tool object.
    """

    context_id: str
    llm: object
    prompts: dict[str, object] = field(default_factory=dict)
    tools: dict[str, object] = field(default_factory=dict)


def _get_tool_name(obj: object) -> str:
    """Return a human-friendly default name for a built tool object.

    Name resolution priority:
    1. `obj.__name__` (functions, classes)
    2. `obj.name` attribute
    3. class name (`obj.__class__.__name__`)
    4. string representation `str(obj)`
    """
    if hasattr(obj, "__name__"):
        return obj.__name__
    if hasattr(obj, "name"):
        return obj.name
    if hasattr(obj, "__class__"):
        return obj.__class__.__name__
    return str(obj)


def _normalize_outputs(outputs: str | list[str] | dict[str, str]) -> str:
    """Return a deterministic string representation of node outputs."""
    if isinstance(outputs, str):
        return outputs
    if isinstance(outputs, list):
        return "__".join(outputs)
    if isinstance(outputs, dict):
        # use values (dataset names), not function output keys
        return "__".join(outputs.values())
    return str(outputs)


@experimental
def llm_context_node(
    *,
    outputs: str,
    llm: str,
    prompts: list[str],
    tools: list[_ToolConfig] | None = None,
    name: str | None = None,
) -> Node:
    """Create a Kedro node that builds an `LLMContext` at runtime.

    Args:
        outputs: Name of the output dataset that will receive the `LLMContext`.
        llm: Name of the Kedro dataset containing the LLM instance.
        prompts: List of dataset names containing prompt content.
        tools: Optional list of tool configurations created via `tool(...)`.
            Each tool declares the Kedro inputs required to construct it.
        name: Optional name for the node and for the created context.

    Returns:
        A Kedro Node that loads all declared datasets, instantiates tools,
        collects prompt values, and returns an `LLMContext`.

    Example:
    ```python
    llm_context_node(
        name="response_agent_context_node",
        outputs="response_generation_context",
        llm="llm",
        prompts=["tool_prompt", "response_prompt"],
        tools=[
            tool(build_get_user_claims, "db_engine"),
            tool(build_lookup_docs, "docs", "params:docs_matches"),
            tool(build_create_claim, "db_engine"),
        ],
    )
    ```
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

    def construct_context(llm: object, **kwargs: dict[str, Any]) -> LLMContext:
        """Node execution: build an LLMContext using loaded datasets."""
        # Collect prompts
        prompts_dict = {p: kwargs[p] for p in prompts}

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
            context_id=name or f"llm_context_node__{_normalize_outputs(outputs)}",
            llm=llm,
            prompts=prompts_dict,
            tools=built_tools,
        )

    return node(func=construct_context, inputs=inputs, outputs=outputs, name=name)
