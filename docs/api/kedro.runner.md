# kedro.runner

::: kedro.runner
    options:
      docstring_style: google
      members: false
      show_source: false

| Name                          | Type       | Description                                      |
|-------------------------------|------------|--------------------------------------------------|
| [`kedro.runner.run_node`](#kedro.runner.run_node) | Function   | Runs a single node in isolation.                |
| [`kedro.runner.AbstractRunner`](#kedro.runner.AbstractRunner) | Class      | Abstract base class for all Kedro runners.      |
| [`kedro.runner.SequentialRunner`](#kedro.runner.SequentialRunner) | Class      | Runs nodes sequentially in a pipeline.          |
| [`kedro.runner.ParallelRunner`](#kedro.runner.ParallelRunner) | Class      | Runs nodes in parallel in a pipeline.           |
| [`kedro.runner.ThreadRunner`](#kedro.runner.ThreadRunner) | Class      | Runs nodes in parallel using threads.           |

::: kedro.runner.run_node
    options:
      show_source: true

::: kedro.runner.AbstractRunner
    options:
      members: true
      show_source: true

::: kedro.runner.ParallelRunner
    options:
      members: true
      show_source: true

::: kedro.runner.SequentialRunner
    options:
      members: true
      show_source: true

::: kedro.runner.ThreadRunner
    options:
      members: true
      show_source: true