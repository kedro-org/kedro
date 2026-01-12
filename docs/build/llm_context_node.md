<!-- vale Kedro.headings = NO -->
# LLM context nodes
<!-- vale Kedro.headings = YES -->

## Overview

!!! warning
    This functionality is experimental and may change or be removed in future releases. Experimental features follow the process described in  [`docs/about/experimental.md`](../about/experimental.md).

LLM context nodes provide a structured way to construct an `LLMContext` inside a Kedro pipeline.
An `LLMContext` bundles together:

- An LLM instance.
- One or more prompt datasets.
- Optionally, dynamically constructed tool objects.

The resulting context is a regular Kedro dataset that can be passed downstream to nodes responsible
for LLM execution, agent orchestration, or workflow control.

This feature focuses on **composition**, not execution: it prepares everything required to run an LLM
without invoking the model itself.

## Node interfaces

Two similar interfaces are provided:

- **Functional API**: `llm_context_node(...)`
- **Class-based API**: `LLMContextNode(...)`

Both APIs produce a standard Kedro `Node` and are fully interchangeable. The functional API is a thin
wrapper around `LLMContextNode` and exists for consistency with Kedro’s existing `node(...)` helpers.

Use whichever style best fits your pipeline definitions.

## When to use an LLM context node

Use an LLM Context Node when you want to:

- Cleanly separate LLM configuration from execution logic.
- Reuse the same LLM, prompts, or tools across multiple downstream nodes.
- Integrate agent frameworks (for example LangGraph, OpenAI Agents, AutoGen) into a Kedro pipeline.
- Treat LLM setup as a first-class pipeline artifact.

LLM context nodes are **not** responsible for:

- Managing conversational history or token context windows.
- Executing or calling the LLM.
- Implementing agent control flow.

## Basic usage

At runtime, Kedro loads the `llm`, `system_prompt`, and `user_prompt` datasets and produces an `LLMContext` object as the node output.

Tools are declared using the `tool()` helper, which specifies a tool constructor function and the Kedro datasets (including `params:`) required to build the tool.

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

### Using LLM

The `llm` argument of LLM context node must reference a Kedro dataset that returns an initialized LLM or LLM wrapper object.

In practice, this is typically provided by a core LLM dataset, such as
[kedro_datasets.langchain.ChatOpenAIDataset](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets/langchain.ChatOpenAIDataset/),
which encapsulates all LLM-specific configuration (model name, credentials, timeouts, retries, and more).

At runtime, Kedro loads the dataset and passes the resulting LLM object directly
into the constructed `LLMContext`. The context node does not invoke the LLM itself;
it makes the LLM available to downstream nodes, agents, or execution
frameworks (for example LangChain, LangGraph, OpenAI Agents, or AutoGen).

### Using prompts

Prompts are treated as datasets, not inline strings.

Each prompt listed in `llm_context_node(prompts=[...])` must correspond to a Kedro
dataset that returns prompt content when loaded.

For example, prompts can be backed by experimental prompt datasets such as:

- [kedro_datasets_experimental.langchain.LangChainPromptDataset](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets_experimental/langchain.LangChainPromptDataset/)
- [kedro_datasets_experimental.langfuse.LangfusePromptDataset](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets_experimental/langfuse.LangfusePromptDataset/)
- [kedro_datasets_experimental.opik.OpikPromptDataset](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets_experimental/opik.OpikPromptDataset/)

At runtime, all prompt datasets are loaded by Kedro and made available in
`LLMContext.prompts` as a mapping:
```python
{
    "system_prompt": "...",
    "tool_prompt": "...",
}
```

This keeps prompt management fully declarative and aligned with Kedro’s dataset model,
while allowing different prompt backends to be swapped without changing pipeline code.

### Using tools

Tools used with `llm_context_node` are defined as builder functions.
A tool builder is a regular Python function that receives datasets loaded by Kedro
(for example database engines, indexes, or documents) and returns a callable or tool object
that can be used by an LLM or agent framework.

````python
from langchain_core.tools import tool

def build_lookup_docs(docs, max_matches: int):
    """Create a document lookup tool from a document store."""

    @tool
    def lookup(query: str) -> list[str]:
        return docs.search(query, limit=max_matches)

    return lookup
````

The arguments passed to the tool’s callable (for example `lookup(query: str)`) are not provided by Kedro, but are dynamically injected by the LLM at execution time based on the model’s tool-calling or function-calling mechanism.
Kedro is responsible for supplying the builder inputs (datasets and parameters) required to construct the tool, not the arguments used when the tool is called.

The tool is then registered in the pipeline using the `tool()` helper:

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

Tool instantiation is intentionally lightweight and deterministic.
All declared tool inputs are validated and loaded by Kedro before execution.
Tool objects are instantiated at node runtime and tool names are automatically
derived from the returned objects (for example function name).

## Composing and consuming an LLM context

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

This node produces an `LLMContext` dataset containing:

- `context.llm` - the loaded LLM instance
- `context.prompts` - a mapping of prompt names to prompt content
- `context.tools` - a mapping of tool names to instantiated tool objects

### 2. Define a node that consumes the `LLMContext`

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

This structure keeps configuration in the `LLMContextNode`, execution logic in downstream nodes and data flow fully visible to Kedro.

## Design notes and limitations

- Each LLM context node instantiates its tools independently. Tool reuse is achieved by reusing datasets and parameters, not shared runtime objects.
- All inputs are standard Kedro datasets and are validated before execution.
- The node returns a standard Kedro `Node` and does not introduce new execution semantics.
