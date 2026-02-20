# Multirun Design Considerations for KedroSession

Beyond the core requirements (concurrent runs, data isolation, runtime dataset injection), here are critical design considerations when implementing multirun support for `KedroSession`.

---

## 1. **Hook Manager & Lifecycle Events Amplification**

### Current State
- Hooks like `before_pipeline_run`, `after_pipeline_run`, `before_node_run`, `after_node_run` are tied to individual runs.
- All hooks receive `run_id` as a parameter, which is currently set to `session_id`.
- Hooks are created once per session (in `KedroSession.__init__`), not per-run.

### Multirun Implications
- **Problem**: With multirun, multiple `run_id`s will exist within a single session. If hooks maintain state (e.g., logging aggregation, metrics collection), they may conflate data across runs unless explicitly scoped by `run_id`.
- **Solution**: 
  - Ensure hooks are designed to be **idempotent and run-scoped** by `run_id`.
  - Document that hooks should NOT maintain mutable state across runs; if they do, they must explicitly manage per-`run_id` partitions.
  - Consider adding a new hook like `after_session_run` (fired after each individual run completes) or `after_all_runs` (fired after the session's multirun completes) to allow cleanup/aggregation logic.
  - Hooks should be tested with multiple sequential runs to catch state leakage.

### Recommendations
- Add documentation in hook specs warning that hooks will be called multiple times per session if multirun is used.
- Consider adding a `session_id` field to `run_params` passed to hooks so they can distinguish between multiple runs within the same session.
- Test hook behavior under multirun scenarios in CI/CD.

---

## 2. **Session Store & Metadata Persistence**

### Current State
- `BaseSessionStore` is initialized once per session with a single `session_id`.
- Stores session-level metadata (project_path, env, git info, CLI context).
- Exceptions from failed runs are logged to `_store["exception"]`.

### Multirun Implications
- **Problem**: 
  - Currently, if a run fails, the exception is stored at `_store["exception"]`, overwriting any previous exception. With multirun, you lose visibility into which run failed and why.
  - Session metadata (e.g., env, runtime_params) is fixed at session creation time; multirun may vary env or runtime_params per run.
  - There's no native way to record per-run metadata (start time, end time, output paths, status) within the store.

### Recommendations
- **Extend store schema** to support per-run records:
  ```python
  {
    "session_id": "...",
    "project_path": "...",
    "runs": [
      {
        "run_id": "...",
        "env": "...",
        "runtime_params": {...},
        "status": "success|failed|skipped",
        "exception": {...},  # only if failed
        "start_time": "...",
        "end_time": "...",
        "outputs_location": "...",  # where results are saved
        "pipeline_names": [...],
      },
      ...
    ]
  }
  ```
- **Avoid overwriting exception data**: Append run-specific errors to a list or per-run record.
- **Consider implementing a session registry** (e.g., a database table or distributed log) if multirun becomes a frequent pattern for production workflows. This allows:
  - Querying runs by session, time, status, etc.
  - Parallel run tracking across multiple machines.
  - Audit trail for compliance.

---

## 3. **Dataset Release & Memory Management**

### Current State
- `AbstractDataset.release()` is available to free cached data.
- `DataCatalog.release(ds_name)` releases a specific dataset.
- In-memory datasets (e.g., `MemoryDataset`, `SharedMemoryDataset`) hold data in RAM.

### Multirun Implications
- **Problem**:
  - Between sequential runs in the same session, intermediate in-memory datasets are NOT automatically released.
  - If you run 1000 sequential runs loading large datasets into memory, memory usage compounds.
  - For `SharedMemoryDataset` (used with `ParallelRunner`), shared memory is tied to a manager; if not properly cleaned up, semaphores and resources leak.

### Recommendations
- **Add explicit cleanup** in `KedroSession.run()` after each run completes:
  ```python
  try:
    run_result = runner.run(...)
  finally:
    # Release all in-memory datasets from the catalog to free memory
    for ds_name in catalog:
      try:
        catalog.release(ds_name)
      except Exception:
        self._logger.debug(f"Could not release {ds_name}")
  ```
- **For `SharedMemoryDataCatalog`**: Ensure the underlying multiprocessing manager is properly shut down/cleaned up after the run (or provide a context manager interface).
- **Document memory implications**: Warn users that sequential runs will accumulate memory unless datasets are explicitly released or catalogs are garbage-collected between runs.
- **Consider adding a `multirun_mode` flag** that automatically releases datasets after each run (or enables other memory-conscious behaviors).

---

## 4. **Catalog Lazy Loading & State Management**

### Current State
- Catalogs use `_LazyDataset` to defer instantiation until datasets are accessed.
- Datasets are materialized on first access and then cached in the catalog.

### Multirun Implications
- **Problem**:
  - If you call `load()` on a dataset in run 1, it gets materialized and cached. In run 2, if the same dataset is accessed, it may return the old cached instance instead of materializing a fresh one (depending on whether the catalog is fresh or reused).
  - Even though `KedroSession.run()` calls `context._get_catalog()` afresh per run (creating a new catalog instance), if you reuse a context across runs, the context's internal state may be stale.

### Recommendations
- **Always create a fresh `KedroContext` per run** (already done by calling `load_context()` per run, but enforce this in multirun code).
- **Document that contexts are not reusable across runs**. If a user caches a context, behavior is undefined in multirun.
- **Consider adding a `reset()` method to `KedroContext`** (or ensure contexts are lightweight enough to discard and recreate).
- **For parameters**: Ensure `_runtime_params` is deep-copied when passed into a new run so that mutations in one run don't affect the next. (Already done via `deepcopy` in context initialization, but verify in tests.)

---

## 5. **Run ID Generation & Uniqueness**

### Current State
- `run_id` is currently set to `session_id` (a timestamp).
- Timestamps are generated via `generate_timestamp()` and are unique only to microsecond precision.

### Multirun Implications
- **Problem**:
  - If two runs start within the same microsecond, their `run_id`s collide.
  - In a high-concurrency scenario or on fast systems, timestamp collisions are possible.
  - For datasets saved to a versioned path, collisions result in overwritten outputs.

### Recommendations
- **Use UUID or UUID + timestamp** for `run_id` to ensure global uniqueness:
  ```python
  import uuid
  run_id = f"{generate_timestamp()}-{uuid.uuid4().hex[:8]}"
  ```
- **Document `run_id` format** and ensure it's safe for use in filesystem paths (no special characters that break paths).
- **Validate uniqueness** in tests by running many rapid sequential runs and checking that all outputs are distinct.
- **For distributed multirun**: If runs are distributed across multiple machines, ensure centralized `run_id` generation (e.g., via a service) or use UUIDs (which are collision-resistant by design).

---

## 6. **Pipeline Filtering & Run Scope**

### Current State
- `Pipeline.filter()` is applied per-run to select which nodes execute.
- Node filters include: `tags`, `from_nodes`, `to_nodes`, `node_names`, `from_inputs`, `to_outputs`, `namespaces`.

### Multirun Implications
- **Problem**:
  - If you run the same pipeline with different filters in sequential runs, intermediate datasets from run 1 may be present in the `load_versions` for run 2, causing cross-run dependencies that are hard to debug.
  - Filtered pipelines may only run a subset of nodes; if datasets from skipped nodes are expected in run 2, run 2 may fail or load stale data.

### Recommendations
- **Document run filter scope**: Filters apply only to the current run; they don't persist state for subsequent runs.
- **Consider adding explicit run-scoped input/output validation**: Before a run, check that all required inputs are available and come from the expected run or load_versions.
- **Add a validation mode** (optional) that checks for cross-run dataset dependencies and warns users if run 1's outputs are being loaded by run 2 (to catch accidental dependencies).
- **For complex multirun workflows**, consider using a **pipeline registry or DAG manager** that tracks dependencies between runs (e.g., "run 2 depends on outputs from run 1").

---

## 7. **Error Handling & Partial Failures**

### Current State
- If a node fails, the runner catches the exception and invokes `on_node_error` hook.
- If a pipeline fails, the exception is re-raised and caught by `KedroSession.run()`, which logs it to the store.

### Multirun Implications
- **Problem**:
  - If run 1 fails partway through, run 2 may load partial outputs from run 1 (if they share a dataset namespace).
  - If a multirun comprises N runs and run 5 fails, what happens to runs 6–N? Do they run, skip, or stop?
  - Error context (which run, which node) is lost if not carefully threaded through exceptions.

### Recommendations
- **Define failure policy for multirun**:
  - **Fail-fast**: Stop on the first failed run (default for safety).
  - **Continue-on-error**: Continue running subsequent runs, collect errors, report at the end.
  - **Retry-on-error**: Retry a failed run N times before moving to the next.
  - Document which policy is active and make it configurable.

- **Enhance exception information**:
  ```python
  class MultirunException(KedroSessionError):
    def __init__(self, run_id: str, original_error: Exception):
      self.run_id = run_id
      self.original_error = original_error
  ```
  - Ensure traceback and run context are preserved.

- **Cleanup on failure**:
  - If a run fails, decide whether to keep or delete partially-saved outputs:
    - **Keep**: Allows inspection for debugging; may pollute the data catalog.
    - **Delete**: Ensures a clean state; loses data for inspection.
  - Make this configurable (e.g., `cleanup_on_error=True/False`).

- **Provide rollback mechanism** (optional for advanced use cases):
  - For transactional datasets (e.g., databases), support rollback on failure.
  - For file-based datasets, consider a trash bin or versioning system.

---

## 8. **Load Versions & Cross-Run Dependencies**

### Current State
- `load_versions` is a dict mapping dataset names to version timestamps.
- It's passed to `runner.run()` and used during node execution to load specific versions of datasets.

### Multirun Implications
- **Problem**:
  - If run 1 saves dataset `X` with `run_id_1`, and run 2 wants to load that version, run 2 must pass `load_versions={"X": run_id_1}`. There's no mechanism to automatically resolve inter-run dependencies.
  - Complex dependency chains (run 1 → run 2 → run 3) require manual orchestration.

### Recommendations
- **Document load_versions usage in multirun**:
  - Users must explicitly specify which versions to load in each run via `load_versions` parameter.
  - Example: 
    ```python
    with KedroSession.create() as session:
      result_1 = session.run(runtime_params={...})
      run_id_1 = result_1.get("run_id")  # hypothetical
      result_2 = session.run(runtime_params={...}, load_versions={"intermediate": run_id_1})
    ```

- **Provide helpers** to extract `run_id` from run results:
  - Add `run_id` to the `run_result` dict returned by `runner.run()` so users can easily chain runs.

- **Consider a multirun orchestrator** (future enhancement):
  - A higher-level abstraction that manages dependencies between runs (e.g., a workflow DAG or state machine).
  - Automatically resolves load_versions based on declared dependencies.

---

## 9. **Transcodable Datasets & Format Switching**

### Current State
- Pipeline supports transcoding (e.g., `my_dataset@csv`, `my_dataset@parquet`) to save the same logical dataset in multiple formats.
- Transcoding is handled transparently by the pipeline and catalog.

### Multirun Implications
- **Problem**:
  - Transcoded datasets add complexity: if run 1 saves `my_dataset@csv` and run 2 loads `my_dataset@parquet`, are they the same logical dataset or different?
  - In multirun, if different runs use different transcodings, the catalog may have multiple versions in different formats, complicating cleanup and versioning.

### Recommendations
- **Enforce transcoding consistency** within a session:
  - Document that transcoding should be consistent across all runs in a multirun.
  - Optionally, add validation to warn if different runs use different transcodings for the same dataset.

- **Consider transcoding-aware versioning**:
  - Include transcoding format in the versioned path (e.g., `data/v1.0-run_id_1@csv/...`).

- **Test transcoding in multirun scenarios**.

---

## 10. **Async Execution & Thread Safety**

### Current State
- `AbstractRunner` supports `is_async=True`, which loads/saves datasets asynchronously with threads.
- `SharedMemoryDataCatalog` uses multiprocessing for data sharing.

### Multirun Implications
- **Problem**:
  - If multirun runs within the same process (e.g., Python REPL or Jupyter), thread-local or process-local state may be shared across runs.
  - If a run uses async I/O (thread-based) and another uses `SharedMemoryDataCatalog` (process-based), mixing them may cause deadlocks or data corruption.

### Recommendations
- **Document async + multirun interaction**:
  - Advise that each run should use the same async setting (don't mix async and non-async runs in the same session).

- **For `ParallelRunner` + multirun**:
  - Ensure `SharedMemoryDataCatalog`'s manager is properly cleaned up between runs.
  - Test concurrent multirun with `ParallelRunner` to catch race conditions.

- **Thread-safety guarantees**:
  - Document which catalog operations are thread-safe and which are not.
  - Ensure hooks don't share mutable state across async operations.

---

## 11. **Hooks Execution Order & Composition**

### Current State
- Hooks are registered via `_register_hooks()` in `KedroSession.__init__()`.
- Multiple hooks can be registered for the same lifecycle event; they execute in registration order.

### Multirun Implications
- **Problem**:
  - With multiple runs, hooks fire multiple times. If hooks have dependencies or shared state, execution order becomes critical.
  - If hook A modifies catalog and hook B expects the original catalog, the order matters.

### Recommendations
- **Document hook ordering guarantees** (or lack thereof) in multirun.
- **Recommend idempotent, stateless hooks** for multirun scenarios.
- **Consider adding hook context** to disambiguate which run a hook is executing for:
  ```python
  hook_manager.hook.before_pipeline_run(
    run_id=run_id,  # new
    run_index=1,    # which run in the multirun (0-indexed)
    total_runs=3,   # total runs in this multirun
    run_params=...,
    pipeline=...,
    catalog=...,
  )
  ```

---

## 12. **Monitoring, Logging & Observability**

### Current State
- Logging is session-based; logs are emitted to stdout/stderr and log files.
- Run parameters are logged via `before_pipeline_run` and `after_pipeline_run` hooks.

### Multirun Implications
- **Problem**:
  - Logs from multiple runs are interleaved in the same log file, making it hard to trace a single run.
  - No built-in way to correlate logs with specific runs.
  - Metrics (e.g., run duration, node duration) are not aggregated across runs.

### Recommendations
- **Add run-scoped logging**:
  - Include `run_id` in all log messages (via a logging context variable or filter).
  - Optionally, write per-run log files: `logs/run_{run_id}.log`.

- **Collect run-level metrics**:
  - Start/end time per run.
  - Duration per run and per node.
  - Memory usage per run.
  - Error/warning counts per run.
  - Store in store or export to monitoring system.

- **Consider structured logging** (e.g., JSON logs):
  - Allows parsing and analysis of multirun execution.
  - Enables integration with ELK, Splunk, or other log aggregation systems.

- **Add progress tracking for multirun**:
  - "Run 3 of 10 completed" style progress indication.
  - Estimated time remaining.

---

## 13. **Configuration Scope & Multi-Environment Runs**

### Current State
- Environment is fixed at session creation via `env` parameter or `KEDRO_ENV` env var.
- All runs in a session inherit the same environment.

### Multirun Implications
- **Problem**:
  - If you want to run the same pipeline against multiple environments (e.g., `local`, `dev`, `prod`) in a single session, you must create multiple sessions.
  - Configuration changes between runs require recreating contexts.

### Recommendations
- **Allow per-run `env` override** (optional enhancement):
  ```python
  session.run(env="dev", ...)
  session.run(env="prod", ...)
  ```
  - Requires creating fresh contexts with different envs for each run.

- **Document multi-environment patterns**:
  - Using external orchestrators (e.g., Airflow) to manage multi-environment runs.
  - Using separate sessions for each environment.

- **Avoid implicit env switching**: Don't allow env to change mid-run; always create a fresh context.

---

## 14. **Backward Compatibility & Migration Path**

### Current State
- `KedroSession` currently enforces one run per session (raises `KedroSessionError` on second call to `run()`).
- Existing code relies on this 1:1 mapping.

### Multirun Implications
- **Breaking change**: Removing the single-run restriction is a breaking change for code that relies on the exception.

### Recommendations
- **Phased rollout**:
  1. Phase 1: Add multirun support via opt-in flag (e.g., `multirun=True` param to `create()`).
  2. Phase 2: Make multirun the default; provide deprecation warning for single-run-only code.
  3. Phase 3: Remove single-run enforcement in major version bump.

- **Migration guide**:
  - Show users how to adapt single-run code to use multirun.
  - Highlight differences in error handling, dataset versioning, etc.

- **Feature flag**: Use feature flag or settings to enable/disable multirun for staged rollout.

---

## 15. **Testing & Validation**

### Multirun-Specific Tests
- **Sequential run tests**: Verify that N sequential runs produce independent outputs with no crosstalk.
- **Concurrent run tests**: If concurrent multirun is supported, verify thread/process safety.
- **Error recovery tests**: Verify behavior when runs fail partway through.
- **Memory tests**: Verify no memory leaks over many sequential runs.
- **Load_versions tests**: Verify cross-run dataset loading works correctly.
- **Hook tests**: Verify hooks fire correctly for each run and don't share state.
- **Integration tests**: End-to-end multirun workflow with realistic pipelines.

### Recommended Test Coverage
- Add fixtures for multirun setup/teardown.
- Mock datasets to verify versioning and cleanup.
- Test with `SequentialRunner`, `ParallelRunner`, and `ThreadRunner`.
- Test with different catalog implementations.

---

## Summary Table of Considerations

| Consideration | Impact | Complexity | Recommendation |
|---|---|---|---|
| Hook state leakage | High | Medium | Document & test hook idempotence |
| Session store metadata | High | Low | Extend store schema for per-run records |
| Memory accumulation | High | Low | Add explicit dataset release after each run |
| Lazy catalog state | Medium | Low | Always create fresh contexts |
| Run ID collisions | High | Low | Use UUID + timestamp |
| Pipeline filter crosstalk | Medium | Medium | Document and validate run-scoped filters |
| Multirun error policy | High | Medium | Define and make configurable |
| Load versions orchestration | Medium | High | Provide helpers; consider orchestrator |
| Transcoding consistency | Low | Low | Document & validate |
| Async + multirun safety | Medium | Medium | Document & test |
| Hook ordering | Medium | Low | Document; add run context |
| Logging & observability | High | Medium | Add run-scoped logging & metrics |
| Multi-environment support | Low | Medium | Document patterns; consider opt-in flag |
| Backward compatibility | High | High | Phased rollout with feature flag |
| Testing | High | High | Comprehensive multirun test suite |

---

## Next Steps

1. **Implement core multirun** (unique run_id, fresh catalogs per run, dataset release).
2. **Extend session store** to track per-run metadata.
3. **Add per-run logging** and run-scoped log files.
4. **Comprehensive testing** with all runners and catalog types.
5. **Documentation** with multirun patterns and best practices.
6. **Feature flag** for phased rollout.
7. **Observability improvements** (metrics, dashboards for multirun execution).
