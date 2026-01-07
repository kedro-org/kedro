# LLM Context Nodes

## Overview

!!! warning
    This functionality is experimental and may change or be removed in future releases. Experimental features follow the process described in  [`docs/about/experimental.md`](../about/experimental.md).

LLM Context Nodes provide a structured way to construct an `LLMContext` inside a Kedro pipeline.
An `LLMContext` bundles together:

- an LLM instance,
- one or more prompt datasets,
- optionally, dynamically constructed tool objects.

The resulting context is a regular Kedro dataset that can be passed downstream to nodes responsible
for LLM execution, agent orchestration, or workflow control.

This feature focuses on **composition**, not execution: it prepares everything required to run an LLM
without invoking the model itself.

## Node interfaces

Two equivalent interfaces are provided:

- **Functional API**: `llm_context_node(...)`
- **Class-based API**: `LLMContextNode(...)`

Both APIs produce a standard Kedro `Node` and are fully interchangeable. The functional API is a thin
wrapper around `LLMContextNode` and exists for consistency with Kedro’s existing `node(...)` helpers.

Use whichever style best fits your pipeline definitions.

## When to use an LLM Context Node

Use an LLM Context Node when you want to:

- cleanly separate LLM configuration from execution logic,
- reuse the same LLM, prompts, or tools across multiple downstream nodes,
- integrate agent frameworks (e.g. LangGraph, OpenAI Agents, AutoGen) into a Kedro pipeline,
- treat LLM setup as a first-class pipeline artifact.

LLM Context Nodes are **not** responsible for:

- managing conversational history or token context windows,
- executing or calling the LLM,
- implementing agent control flow.

## Basic usage

At runtime, Kedro loads the `llm`, `system_prompt`, and `user_prompt` datasets and produces an `LLMContext` object as the node output.

Tools are declared using the `tool()` helper, which specifies:

- a tool constructor function,
- the Kedro datasets (including `params:`) required to build the tool.

### Functional API

```python
from kedro.pipeline import llm_context_node

llm_context_node(
    name="basic_llm_context",
    outputs="llm_context",
    llm="llm",
    prompts=["system_prompt", "user_prompt"],
)
```

### Class-based API

```python
from kedro.pipeline import LLMContextNode

LLMContextNode(
    name="basic_llm_context",
    outputs="llm_context",
    llm="llm",
    prompts=["system_prompt", "user_prompt"],
)
```

### Using tools

Tool instantiation is intentionally lightweight and deterministic. All declared tool inputs are validated and loaded by Kedro before execution. Tool objects are instantiated at node runtime and tool names are automatically derived from the returned objects (e.g. function name).

```python
from kedro.pipeline import llm_context_node, tool

llm_context_node(
    name="llm_context_with_tools",
    outputs="llm_context",
    llm="llm",
    prompts=["tool_prompt"],
    tools=[
        tool(build_lookup_docs, "docs", "params:max_matches"),
        tool(build_create_claim, "db_engine"),
    ],
)
```

## Composing and consuming an `LLMContext`

This example shows how `LLMContext` acts as a boundary object between configuration and execution.

### 1. Define the LLM context node
```python
from kedro.pipeline import LLMContextNode, tool

response_context_node = LLMContextNode(
    name="response_context",
    outputs="response_context",
    llm="llm",
    prompts=["system_prompt", "response_prompt"],
    tools=[
        tool(build_get_user_claims, "db_engine"),
        tool(build_lookup_docs, "docs", "params:docs_matches"),
    ],
)
```

This node produces an LLMContext dataset containing:

- `context.llm` - the loaded LLM instance
- `context.prompts` - a mapping of prompt names to prompt content
- `context.tools` - a mapping of tool names to instantiated tool objects

### 2. Define a node that consumes the LLMContext

```python
from kedro.pipeline import Node
from kedro.pipeline.llm_context import LLMContext

def generate_response(context: LLMContext) -> str:
    return context.llm.run(
        prompts=context.prompts,
        tools=context.tools,
    )

response_node = Node(
    func=generate_response,
    inputs="response_context",
    outputs="response",
)
```

The execution node remains unaware of how the LLM, prompts, or tools were constructed.

### 3. Assemble the pipeline

```python
from kedro.pipeline import Pipeline

pipeline = Pipeline([
    response_context_node,
    response_node,
])
```

This structure keeps:

- configuration in the LLM Context Node,
- execution logic in downstream nodes,
- data flow fully visible to Kedro.

## Design notes and limitations

- Each `LLMContextNode` instantiates its tools independently. Tool reuse is achieved by reusing datasets and parameters, not shared runtime objects.
- If a tool requires caching or shared state, this should be implemented within the tool itself or modeled explicitly as a Kedro dataset.
- All inputs are standard Kedro datasets and are validated before execution.
- The node returns a standard Kedro `Node` and does not introduce new execution semantics.

This design keeps LLM Context Nodes predictable, composable, and aligned with Kedro’s core principles.
