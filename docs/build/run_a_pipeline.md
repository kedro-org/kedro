# Run a pipeline

## Runners

Runners are the execution mechanisms used to run pipelines. They all inherit from `AbstractRunner`.

### `SequentialRunner`

Use `SequentialRunner` to execute pipeline nodes one-by-one based on their dependencies.

We recommend using `SequentialRunner` in cases where:

- the pipeline has limited branching
- the pipeline is fast
- the resource-consuming steps require most of a scarce resource (e.g., significant RAM, disk memory or CPU)

Kedro uses `SequentialRunner` by default, so to execute the pipeline sequentially:

```bash
kedro run
```

You can also explicitly use `SequentialRunner` as follows:

```bash
kedro run --runner=SequentialRunner
```

### `ParallelRunner`

#### Multiprocessing

You can alternatively run the nodes within the pipeline concurrently, using a `ParallelRunner` as follows:
```bash
kedro run --runner=ParallelRunner
```

For the `ParallelRunner`, it is possible to manually select which multiprocessing start method is going to be used.

- `fork`: The child process is created as a copy of the parent process. This is fast but can cause issues with libraries that use threads or manage internal state. Default on most Unix systems.

- `spawn`: The child process starts fresh, importing the main module and only inheriting necessary resources. This is safer and more compatible with many libraries, but requires all objects to be picklable. Default on Windows and macOS (Python 3.8+).

To control which multiprocessing start method is going to be used by `ParallelRunner`, you can set the value `spawn` or `fork` to the `KEDRO_MP_CONTEXT` environment variable. If neither of those is set, the runner will use the system's default.

#### Multithreading
While `ParallelRunner` uses multiprocessing, you can also run the pipeline with multithreading for concurrent execution by specifying `ThreadRunner` as follows:

```bash
kedro run --runner=ThreadRunner
```

!!! note
    `SparkDataset` doesn't work correctly with `ParallelRunner`. To add concurrency to the pipeline with `SparkDataset`, you must use `ThreadRunner`.

For more information on how to maximise concurrency when using Kedro with PySpark, read our guide on [how to build a Kedro pipeline with PySpark](../integrations-and-plugins/pyspark_integration.md).

## Custom runners

If the built-in Kedro runners do not meet your requirements, you can also define your own runner within your project. For example, you may want to add a dry runner, which lists which nodes would be run without executing them:

??? example "View code"
    ```python
    # in src/<package_name>/runner.py
    from typing import Any, Dict
    from kedro.io import AbstractDataset, KedroDataCatalog, MemoryDataset
    from kedro.pipeline import Pipeline
    from kedro.runner.runner import AbstractRunner
    from pluggy import PluginManager


    class DryRunner(AbstractRunner):
        """``DryRunner`` is an ``AbstractRunner`` implementation. It can be used to list which
        nodes would be run without actually executing anything. It also checks if all the
        necessary data exists.
        """

        def __init__(self, is_async: bool = False, extra_dataset_patterns: Dict[str, Dict[str, Any]] = None):
            """Instantiates the runner class.

            Args:
                is_async: If True, the node inputs and outputs are loaded and saved
                    asynchronously with threads. Defaults to False.
                extra_dataset_patterns: Extra dataset factory patterns to be added to the KedroDataCatalog
                    during the run. This is used to set the default datasets.
            """
            default_dataset_pattern = {"{default}": {"type": "MemoryDataset"}}
            self._extra_dataset_patterns = extra_dataset_patterns or default_dataset_pattern
            super().__init__(is_async=is_async, extra_dataset_patterns=self._extra_dataset_patterns)

        def _run(
            self,
            pipeline: Pipeline,
            catalog: KedroDataCatalog,
            hook_manager: PluginManager = None,
            run_id: str = None,
        ) -> None:
            """The method implementing dry pipeline running.
            Example logs output using this implementation:

                kedro.runner.dry_runner - INFO - Actual run would execute 3 nodes:
                node3: identity([A]) -> [B]
                node2: identity([C]) -> [D]
                node1: identity([D]) -> [E]

            Args:
                pipeline: The ``Pipeline`` to run.
                catalog: The ``KedroDataCatalog`` from which to fetch data.
                hook_manager: The ``PluginManager`` to activate hooks.
                run_id: The id of the run.

            """
            nodes = pipeline.nodes
            self._logger.info(
                "Actual run would execute %d nodes:\n%s",
                len(nodes),
                pipeline.describe(),
            )
            self._logger.info("Checking inputs...")
            input_names = pipeline.inputs()

            missing_inputs = [
                input_name
                for input_name in input_names
                if not catalog._get_dataset(input_name).exists()
            ]
            if missing_inputs:
                raise KeyError(f"Datasets {missing_inputs} not found.")
    ```


And use it with `kedro run` through the `--runner` flag:

```console
$ kedro run --runner=<package_name>.runner.DryRunner
```

## Load and save asynchronously

!!! note
    `ThreadRunner` doesn't support asynchronous load-input or save-output operations.

When processing a node, both `SequentialRunner` and `ParallelRunner` perform the following steps in order:

1. Load data based on node input(s)
2. Execute node function with the input(s)
3. Save the output(s)

If a node has multiple inputs or outputs (e.g., `Node(func, ["a", "b", "c"], ["d", "e", "f"])`), you can reduce load and save time by using asynchronous mode. You can enable it by passing an `--async` flag to the run command as follows:

```bash
$ kedro run --async
...
2020-03-24 09:20:01,482 - kedro.runner.sequential_runner - INFO - Asynchronous mode is enabled for loading and saving data
...
```

!!! note
    All the datasets used in the run have to be [thread-safe](https://www.quora.com/What-is-thread-safety-in-Python) in order for asynchronous loading/saving to work properly.

## Run a pipeline by name

To run the pipeline by its name, you need to add your new pipeline to the `register_pipelines()` function in `src/<package_name>/pipeline_registry.py`:

??? example "View code"
    ```python
    def register_pipelines():
        """Register the project's pipelines.

        Returns:
            A mapping from pipeline names to ``Pipeline`` objects.
        """
        pipelines = find_pipelines()
        pipelines["__default__"] = sum(pipelines.values())
        my_pipeline = pipeline(
            [
                # your definition goes here
            ]
        )
        pipelines["my_pipeline"] = my_pipeline
        return pipelines
    ```


Then, from the command line, execute the following:

```bash
kedro run --pipeline=my_pipeline
```

!!! note
    If you specify `kedro run` without the `--pipeline` option, it runs the `__default__` pipeline from the dictionary returned by `register_pipelines()`.


Further information about `kedro run` can be found in the [Kedro CLI documentation](../getting-started/commands_reference.md#run-the-project).

## Run pipelines with IO

The above definition of pipelines only applies for non-stateful or "pure" pipelines that do not interact with the outside world. In practice, we would like to interact with APIs, databases, files and other sources of data. By combining IO and pipelines, we can tackle these more complex use cases.

By using `DataCatalog` from the IO module we are still able to write pure functions that work with our data and outsource file saving and loading to `DataCatalog`.

Through `DataCatalog`, we can control where inputs are loaded from, where intermediate variables get persisted and ultimately the location to which output variables are written.

In a simple example, we define a `MemoryDataset` called `xs` to store our inputs, save our input list `[1, 2, 3]` into `xs`, then instantiate `SequentialRunner` and call its `run` method with the pipeline and data catalog instances:

??? example "View code"
    ```python
    io = KedroDataCatalog(dict(xs=MemoryDataset()))
    ```

    ```python
    io.list()
    ```

    `Output`:

    ```console
    Out[10]: ['xs']
    ```

    ```python
    io.save("xs", [1, 2, 3])
    ```

    ```python
    SequentialRunner().run(pipeline, catalog=io)
    ```

    `Output`:

    ```console
    Out[11]: {'v': 0.666666666666667}
    ```


## Configure `kedro run` arguments

The [Kedro CLI documentation](../getting-started/commands_reference.md#run-the-project) lists the available CLI options for `kedro run`. You can alternatively supply a configuration file that contains the arguments to `kedro run`.

Here is an example file named `config.yml`, but you can choose any name for the file:


```console
$ kedro run --config=config.yml
```

where `config.yml` is formatted as below (for example):

```yaml
run:
  tags: tag1, tag2, tag3
  pipeline: pipeline1
  runner: ParallelRunner
  node_names: node1, node2
  env: env1
```

The syntax for the options is different when you're using the CLI compared to the configuration file. In the CLI you use dashes, for example for `kedro run --from-nodes=...`, but you have to use an underscore in the configuration file:

```yaml
run:
  from_nodes: ...
```

This is because the configuration file gets parsed by [Click](https://click.palletsprojects.com/en/8.1.x/), a Python package to handle command line interfaces. Click passes the options defined in the configuration file to a Python function. The option names need to match the argument names in that function.

Variable names and arguments in Python may only contain alphanumeric characters and underscores, so it's not possible to have a dash in the option names when using the configuration file.

!!! note
    If you provide both a configuration file and a CLI option that clashes with the configuration file, the CLI option will take precedence.

## Running pipelines programmatically with runners

Kedro runners provide a consistent interface for executing pipelines, whether you're using sequential, threaded, or parallel execution. This section explains how to run pipelines using the Python API and how to handle pipeline outputs.

### Output from `runner.run()`

* The `runner.run()` method **always returns a list of pipeline output dataset names**, regardless of your catalog setup.
* It **does not return the actual data** — you must explicitly load each dataset from the catalog afterward.

```python
from kedro.framework.project import pipelines
from kedro.io import DataCatalog
from kedro.runner import SequentialRunner

# Load your catalog configuration (e.g., from YAML)
catalog = DataCatalog.from_config(catalog_config)

pipeline = pipelines.get("__default__")
runner = SequentialRunner()

# Run the pipeline
output_dataset_names = runner.run(pipeline=pipeline, catalog=catalog)

# Load data for each output
for ds_name in output_dataset_names:
    data = catalog[ds_name].load()
```

### Using `ParallelRunner` with `SharedMemoryDataCatalog`

To support multiprocessing, `ParallelRunner` requires a special catalog: **`SharedMemoryDataCatalog`**.

This catalog:

* Extends `DataCatalog`
* Ensures datasets are safe for multiprocessing
* Uses shared memory for inter-process communication

```python
from kedro.framework.project import pipelines
from kedro.io import SharedMemoryDataCatalog
from kedro.runner import ParallelRunner

# Load catalog config for multiprocessing context
catalog = SharedMemoryDataCatalog.from_config(catalog_config)

pipeline = pipelines.get("__default__")
runner = ParallelRunner()

# Run the pipeline
output_dataset_names = runner.run(pipeline=pipeline, catalog=catalog)

# Load output data
for ds_name in output_dataset_names:
    data = catalog[ds_name].load()
```

### CLI usage

When using the CLI, Kedro **automatically selects the correct catalog** for the chosen runner.

```bash
kedro run                         # Uses SequentialRunner and DataCatalog
kedro run -r ThreadRunner         # Uses ThreadRunner and DataCatalog
kedro run -r ParallelRunner       # Uses ParallelRunner and SharedMemoryDataCatalog
```

You don’t need to worry about which catalog to use — Kedro takes care of that behind the scenes.

### Summary

* `runner.run()` always returns output **dataset names**, not the data itself
* Use `catalog[ds_name].load()` to get the actual data
* `ParallelRunner` requires `SharedMemoryDataCatalog` for multiprocessing
* The Kedro CLI selects the correct catalog automatically
* When using the Python API, **you must choose the appropriate catalog yourself**
