# Kedro Session Architecture: AbstractSession, KedroSession, and KedroServiceSession

## Overview

This document describes the refactored session architecture for Kedro, which introduces a clear separation of concerns through an abstract base class and two concrete implementations for different use cases.

## Architecture

```
AbstractSession (abstract_session.py)
├── KedroSession (session.py)
│   └── Single run per session (traditional behavior)
└── KedroServiceSession (service_session.py)
    └── Multiple concurrent/sequential runs per session (new)
```

### AbstractSession

**File:** `abstract_session.py`

The abstract base class that defines the common interface and shared functionality for all session types.

**Key Responsibilities:**
- Session lifecycle management (creation, closing)
- Hook manager initialization and management
- Store initialization and persistence
- Context loading with optional per-run env/params
- Configuration loading
- Exception logging

**Key Methods:**
- `__init__()` - Initialize session with project metadata
- `load_context()` - Load a KedroContext with optional runtime params/env
- `_get_config_loader()` - Create a config loader
- `close()` - Close session and save store
- `run()` - Abstract method, must be implemented by subclasses

**Properties:**
- `store` - Returns a copy of the session store dictionary
- `_logger` - Returns the session logger

### KedroSession

**File:** `session.py`

Traditional single-run session implementation. Maintains backward compatibility with existing Kedro code.

**Behavior:**
- One run per session (enforced via `_run_called` flag)
- Raises `KedroSessionError` if `run()` is called more than once
- All runs use the same catalog and context
- Suitable for CLI usage and simple workflows

**Key Methods:**
- `create()` - Class method to create a new session
- `run()` - Execute a single pipeline run
- Inherits all lifecycle methods from `AbstractSession`

**Example:**
```python
with KedroSession.create() as session:
    result = session.run(pipeline_names=["__default__"])
```

### KedroServiceSession

**File:** `service_session.py`

New multi-run session implementation designed for concurrent and sequential execution of multiple runs.

**Behavior:**
- Multiple runs per session with independent contexts and catalogs
- Concurrent execution via ThreadPoolExecutor
- Per-run configuration (pipeline, tags, params, env)
- Error handling and progress tracking
- Aggregated result collection

**Key Classes:**

#### RunConfig
Configuration object for a single run.

**Attributes:**
```python
@dataclass
class RunConfig:
    run_id: str                              # Auto-generated unique ID
    pipeline_names: list[str] | None = None
    tags: Iterable[str] | None = None
    runner: AbstractRunner | None = None
    node_names: Iterable[str] | None = None
    from_nodes: Iterable[str] | None = None
    to_nodes: Iterable[str] | None = None
    from_inputs: Iterable[str] | None = None
    to_outputs: Iterable[str] | None = None
    load_versions: dict[str, str] | None = None
    namespaces: Iterable[str] | None = None
    only_missing_outputs: bool = False
    runtime_params: dict[str, Any] | None = None
    env: str | None = None                   # Per-run environment override
```

#### RunResult
Result object from a single run.

**Attributes:**
```python
@dataclass
class RunResult:
    run_id: str                              # From RunConfig
    status: str                              # 'success', 'failed', 'skipped'
    outputs: dict[str, Any] | None = None
    exception: Exception | None = None
    start_time: str | None = None
    end_time: str | None = None
    metadata: dict[str, Any] = field(...)   # Record data from run
```

**Key Methods:**

- `create()` - Class method to create a new service session
- `create_run_config()` - Factory method to create RunConfig instances
- `run()` - Execute a single run
- `run_all()` - Execute multiple runs concurrently
- `run_sequential()` - Execute multiple runs sequentially
- `get_results()` - Retrieve all run results
- `close()` - Cleanup and close session

**Example: Sequential Runs**
```python
with KedroServiceSession.create(max_workers=1) as session:
    configs = [
        session.create_run_config(pipeline_names=["pipeline_1"]),
        session.create_run_config(pipeline_names=["pipeline_2"]),
    ]
    results = session.run_sequential(configs)
    for result in results:
        print(f"Run {result.run_id}: {result.status}")
```

**Example: Concurrent Runs**
```python
with KedroServiceSession.create(max_workers=4) as session:
    configs = [
        session.create_run_config(
            pipeline_names=["pipeline"],
            runtime_params={"param": value}
        )
        for value in range(10)
    ]
    results = session.run_all(configs, continue_on_error=True)
```

## Usage Patterns

### Pattern 1: Single Run (KedroSession)

Use when you need to run a single pipeline once. Maintains backward compatibility.

```python
from kedro.framework.session import KedroSession

with KedroSession.create() as session:
    result = session.run()
```

### Pattern 2: Sequential Multirun (KedroServiceSession with max_workers=1)

Use for deterministic execution where runs depend on each other.

```python
from kedro.framework.session import KedroServiceSession

with KedroServiceSession.create(max_workers=1) as session:
    config_1 = session.create_run_config(pipeline_names=["pipeline_1"])
    result_1 = session.run(config_1)
    
    config_2 = session.create_run_config(
        pipeline_names=["pipeline_2"],
        load_versions={"input": result_1.run_id}
    )
    result_2 = session.run(config_2)
```

### Pattern 3: Concurrent Multirun (KedroServiceSession with max_workers > 1)

Use for parallel execution of independent runs.

```python
from kedro.framework.session import KedroServiceSession

with KedroServiceSession.create(max_workers=4) as session:
    configs = [
        session.create_run_config(
            pipeline_names=["data_pipeline"],
            runtime_params={"data_source": f"source_{i}"}
        )
        for i in range(10)
    ]
    results = session.run_all(configs, continue_on_error=False)
```

### Pattern 4: Hyperparameter Tuning

Use KedroServiceSession to sweep parameters in parallel.

```python
from kedro.framework.session import KedroServiceSession

with KedroServiceSession.create(max_workers=8) as session:
    configs = [
        session.create_run_config(
            pipeline_names=["training_pipeline"],
            runtime_params={"learning_rate": lr, "batch_size": bs}
        )
        for lr in [0.001, 0.01, 0.1]
        for bs in [16, 32, 64]
    ]
    results = session.run_all(configs, continue_on_error=True)
    
    # Find best result
    successful = [r for r in results if r.status == "success"]
    best = max(successful, key=lambda r: r.outputs.get("metrics", {}).get("accuracy", 0))
    print(f"Best run: {best.run_id}")
```

## Backward Compatibility

The refactoring maintains full backward compatibility:

1. **KedroSession** retains its original behavior and API
2. Existing code using `KedroSession` continues to work unchanged
3. **KedroSessionError** is still available for import from `session` module
4. All existing tests pass without modification

## Data Isolation in Concurrent Runs

Each run in `KedroServiceSession` has:

1. **Independent Catalog** - Fresh catalog created per run
2. **Unique Run ID** - Using `generate_timestamp()` + UUID for collision prevention
3. **Versioned Datasets** - `save_version` set to `run_id` for output isolation
4. **Fresh Context** - New `KedroContext` per run with optional env/params overrides

This ensures no data crosstalk between concurrent runs.

## Error Handling

`KedroServiceSession.run_all()` supports two error handling modes:

**Fail-Fast (default):**
```python
results = session.run_all(configs, continue_on_error=False)
# Raises exception on first failed run
```

**Continue-on-Error:**
```python
results = session.run_all(configs, continue_on_error=True)
# Collects failures, returns all results
```

## Progress Tracking

Monitor multirun progress with callback:

```python
def progress_callback(completed: int, total: int) -> None:
    percent = (completed / total) * 100
    print(f"Progress: {completed}/{total} ({percent:.1f}%)")

results = session.run_all(configs, progress_callback=progress_callback)
```

## Store Persistence

Both session types support store persistence:

- **AbstractSession** - Base implementation
- **KedroSession** - Saves per-session metadata
- **KedroServiceSession** - Additionally saves all run results to store under `"runs"` key

```python
# Store structure for KedroServiceSession
{
    "session_id": "...",
    "project_path": "...",
    "runs": [
        {"run_id": "...", "status": "success", "start_time": "...", "end_time": "..."},
        {"run_id": "...", "status": "failed", "start_time": "...", "end_time": "..."},
        ...
    ]
}
```

## Threading Model

`KedroServiceSession` uses Python's `ThreadPoolExecutor` for concurrent execution:

- **Thread-safe** - Each thread gets its own context, catalog, and logger
- **Resource pooling** - Reuses threads across runs
- **Max workers configurable** - Via `max_workers` parameter
- **Graceful shutdown** - All threads joined on session close

## Hooks and Lifecycle

Both session types fire the same hooks:

- `after_context_created` - When context is loaded
- `before_pipeline_run` - Before each pipeline execution
- `after_pipeline_run` - After each pipeline execution
- `on_pipeline_error` - On pipeline execution error

For concurrent runs, hooks are fired per-run with thread safety guaranteed by hook manager.

## Future Enhancements

Potential extensions to this architecture:

1. **Process-based execution** - Replace threads with processes for true parallelism
2. **Async execution** - Support async runners
3. **Distributed execution** - Remote execution on worker nodes
4. **Advanced orchestration** - DAG-based run dependencies
5. **Caching layer** - Share unchanged datasets between runs
6. **Monitoring/metrics** - Built-in run metrics and dashboards

## File Structure

```
kedro/framework/session/
├── __init__.py                 # Public API exports
├── abstract_session.py         # AbstractSession base class
├── session.py                  # KedroSession (traditional)
├── service_session.py          # KedroServiceSession (new)
├── store.py                    # Session store implementations
├── examples.py                 # Usage examples
└── README.md                   # This file
```

## Testing

Both session types should be tested for:

1. **Single runs** - Basic execution
2. **Multiple runs** - Sequential and concurrent
3. **Error handling** - Fail-fast and continue-on-error
4. **Data isolation** - No crosstalk between runs
5. **Hooks** - Correct firing per run
6. **Store persistence** - Metadata saved correctly
7. **Cleanup** - Resources freed on close
8. **Thread safety** - No race conditions in concurrent mode

## See Also

- [MULTIRUN_DESIGN_CONSIDERATIONS.md](../../MULTIRUN_DESIGN_CONSIDERATIONS.md) - Detailed design discussions
- [examples.py](examples.py) - Practical usage examples
