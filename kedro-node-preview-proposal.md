
# Proposal: User-defined `preview` for Kedro nodes (with Kedro-Viz support)

## Summary

Enable Kedro nodes to expose a user-defined preview_ function so projects can visualize complex, non-dataset objects (e.g., compiled LangGraph graphs, ML pipelines, prompts) directly in Kedro-Viz.

---

## Goals
- Let node authors attach a preview function and returns a **`PreviewPayload`** (stable schema).
- Build the minimal Kedro core + Viz glue so previews can be **rendered in Kedro-Viz**.
- Support common render kinds: **`table`, `json`, `image`, `plotly`, `text`, `mermaid`, `custom`**.

---

## Core types (shared contract)

```python
# kedro/pipeline/preview_types.py
from typing import Any, Literal, Callable
import inspect

# This will establish a contract, so anyone implementing a node preview function should return this object
# Also makes plugin developers aware of what to expect from node preview function
class PreviewPayload():
    kind: Literal["mermaid", "json", "text", "image", "plotly", "table", "custom"]
    content: str
    meta: dict[str, Any] | None

# [TODO: Need to clarify on how and what inputs will be available for the preview function. If we want users to pass inputs via args etc, may be a class like below rather than
# just a Callable would be clean]
class NodePreview:
    def __init__(
        self,
        fn: Callable[..., PreviewPayload],
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None
    ) -> None:
        self.fn = fn
        self.args = args or ()
        self.kwargs = kwargs or {}
```

**Why `PreviewPayload`?**
- Serializable over REST for Kedro-Viz.
- Forward-compatible: add more `kind`s later (e.g., `svg`, `vega`, `graphviz`).
- Extensible via `meta` and `custom` kinds.

---

## Approach A: Preview parameter with NodePreview instance

### Kedro core changes

#### 1) Extend `kedro.pipeline.node.Node`

```python
# kedro/pipeline/node.py
from typing import Any, Callable
import inspect
from kedro.pipeline.preview_types import NodePreview, PreviewPayload

class Node:
    def __init__(self, func, inputs, outputs, name=None, tags=None, preview: NodePreview | None = None):
        self.func = func
        self.inputs = inputs
        self.outputs = outputs
        self.name = name
        self.tags = tags or ()
        self._preview = preview

    @property
    def has_preview(self) -> bool:
        """Check if node has preview capability."""
        return self._preview is not None

    def preview(self, *args: Any, **kwargs: Any) -> PreviewPayload | None:
        """Execute preview with intelligent argument merging."""
        if not self._preview:
            return None

        # Merge args and kwargs from NodePreview and method call
        merged_args = self._preview.args + args
        merged_kwargs = {**self._preview.kwargs, **kwargs}

        # Use signature inspection to call the function intelligently
        sig = inspect.signature(self._preview.fn)
        try:
            bound = sig.bind(*merged_args, **merged_kwargs)
            bound.apply_defaults()
            return self._preview.fn(*bound.args, **bound.kwargs)
        except TypeError:
            # Fallback to direct call if signature binding fails
            return self._preview.fn(*merged_args, **merged_kwargs)
```

#### 2) Node constructor helper

```python
# kedro/pipeline/__init__.py
from kedro.pipeline.node import Node
from kedro.pipeline.preview_types import NodePreview

def node(func, inputs, outputs, *, name=None, tags=None, preview=None):
    return Node(func, inputs, outputs, name, tags, preview)
```

### Example usage (LangGraph)

```python
# project/pipelines/agentic/nodes.py
from kedro.pipeline.preview_types import PreviewPayload, NodePreview

def compile_langgraph(cfg):
    # user code that returns compiled graph object with draw_mermaid()
    graph = build_langgraph(cfg)
    return graph

def visualize_langgraph(theme="default", format="mermaid"):
    """Preview function with intelligent args/kwargs merging."""
    content = "graph TD\n  A[Config] --> B[LangGraph]\n  B --> C[Compiled]"
    if theme != "default":
        content = f"%%{{init: {{'theme': '{theme}'}}}}%%\n{content}"
    return {"kind": "mermaid", "content": content, "meta": {"theme": theme}}

# pipeline definition
from kedro.pipeline import node, Pipeline

pipeline = Pipeline([
    node(
        func=compile_langgraph,
        inputs="config",
        outputs="compiled_graph",
        name="compile_langgraph",
        preview=NodePreview(
            fn=visualize_langgraph,
            kwargs={"theme": "dark", "format": "mermaid"}
        ),
    )
])

# Usage: Both NodePreview kwargs and runtime preview() kwargs are merged
# node.preview()  # Uses theme="dark" from NodePreview
# node.preview(theme="light")  # Overrides with theme="light"
```

### Usage Patterns

Simple examples showing args/kwargs support:

```python
# Pattern 1: Simple preview function
def simple_preview():
    return {"kind": "text", "content": "This node generates a graph"}

# Pattern 2: Preview with custom arguments
def themed_preview(theme="light", show_meta=True):
    content = f"Generated visualization with {theme} theme"
    result = {"kind": "text", "content": content}
    if show_meta:
        result["meta"] = {"theme": theme, "timestamp": "2024-01-01"}
    return result

# Usage examples
node(
    func=my_func,
    outputs="result",
    preview=NodePreview(fn=simple_preview)
)

node(
    func=my_func,
    outputs="result",
    preview=NodePreview(
        fn=themed_preview,
        kwargs={"theme": "dark", "show_meta": False}
    )
)
```

---

## Approach B: Preview Function Parameter

```python
# Node class with preview_fn instead of preview object
class Node:
    def __init__(self, func, inputs, outputs, name=None, tags=None, preview_fn: Optional[Callable[..., PreviewPayload]] = None):
        self.func = func
        self.inputs = inputs
        self.outputs = outputs
        self.name = name
        self.tags = tags or ()
        self.preview_fn = preview_fn

    def preview(self, *args, **kwargs) -> Optional[PreviewPayload]:
        if not self.preview_fn:
            return None
        return self.preview_fn(*args, **kwargs)

# Usage
def preview_graph(graph) -> PreviewPayload:
    return {"kind": "mermaid", "content": graph.draw_mermaid()}

node(
    func=compile_graph,
    outputs="compiled_graph",
    preview_fn=preview_graph  # Simple function, no args support
)
```

### Approach C: Decorator-Based

```python
# Decorator to attach preview to function
def with_preview(preview_fn: Callable[..., PreviewPayload]):
    def decorator(func):
        func.__kedro_preview_fn__ = preview_fn
        return func
    return decorator

# Node class checks for decorator
class Node:
    def preview(self, *args, **kwargs) -> Optional[PreviewPayload]:
        preview_fn = getattr(self.func, "__kedro_preview_fn__", None)
        if preview_fn:
            return preview_fn(*args, **kwargs)
        return None

# Usage
@with_preview(lambda graph: {"kind": "mermaid", "content": graph.draw_mermaid()})
def compile_graph(config):
    return build_graph(config)

node(func=compile_graph, outputs="compiled_graph")  # No preview param needed
```

**Trade-offs:**
- **Approach A**: Flexible with args/kwargs support
- **Approach B**: Simplest API, no args support
- **Approach C**: Zero changes to node definition, but less discoverable

---

## Implementation Plan

1. **Core types**: `PreviewPayload` and `NodePreview`
2. **Node enhancement**: Add `preview` or `preview_fn` parameter
3. **Kedro-Viz integration**: https://github.com/kedro-org/kedro-viz/pull/2530

## Questions

1. Clarify on how and what inputs will be available for the preview function at the node level. Since node outputs are generated after the node is run, should the preview_fn even depend on those ? In general what inputs or args should we allow users to pass and how to handle them ?
2. Limit on payload size returned as part of preview_fn ?
3. `kind` or `type` of PreviewPayload content to support in initial release ?
4. Timeout for long-running preview functions (if they depend on remote executions and credential resolutions) ?
