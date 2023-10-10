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

#### Multithreading
While `ParallelRunner` uses multiprocessing, you can also run the pipeline with multithreading for concurrent execution by specifying `ThreadRunner` as follows:

```bash
kedro run --runner=ThreadRunner
```

```{note}
`SparkDataset` doesn't work correctly with `ParallelRunner`. To add concurrency to the pipeline with `SparkDataset`, you must use `ThreadRunner`.
```

For more information on how to maximise concurrency when using Kedro with PySpark, please visit our guide on [how to build a Kedro pipeline with PySpark](../integrations/pyspark_integration.md).

## Custom runners

If the built-in Kedro runners do not meet your requirements, you can also define your own runner within your project. For example, you may want to add a dry runner, which lists which nodes would be run without executing them:

<details>
<summary><b>Click to expand</b></summary>

```python
# in src/<package_name>/runner.py
from kedro.io import AbstractDataset, DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.runner.runner import AbstractRunner
from pluggy import PluginManager


class DryRunner(AbstractRunner):
    """``DryRunner`` is an ``AbstractRunner`` implementation. It can be used to list which
    nodes would be run without actually executing anything. It also checks if all the
    neccessary data exists.
    """

    def create_default_dataset(self, ds_name: str) -> AbstractDataset:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set
        Returns:
            An instance of an implementation of AbstractDataset to be used
            for all unregistered data sets.

        """
        return MemoryDataset()

    def _run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager = None,
        session_id: str = None,
    ) -> None:
        """The method implementing dry pipeline running.
        Example logs output using this implementation:

            kedro.runner.dry_runner - INFO - Actual run would execute 3 nodes:
            node3: identity([A]) -> [B]
            node2: identity([C]) -> [D]
            node1: identity([D]) -> [E]

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            session_id: The id of the session.

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
</details>

And use it with `kedro run` through the `--runner` flag:

```console
$ kedro run --runner=<package_name>.runner.DryRunner
```

## Load and save asynchronously

```{note}
`ThreadRunner` doesn't support asynchronous load-input or save-output operations.
```

When processing a node, both `SequentialRunner` and `ParallelRunner` perform the following steps in order:

1. Load data based on node input(s)
2. Execute node function with the input(s)
3. Save the output(s)

If a node has multiple inputs or outputs (e.g., `node(func, ["a", "b", "c"], ["d", "e", "f"])`), you can reduce load and save time by using asynchronous mode. You can enable it by passing an `--async` flag to the run command as follows:

```bash
$ kedro run --async
...
2020-03-24 09:20:01,482 - kedro.runner.sequential_runner - INFO - Asynchronous mode is enabled for loading and saving data
2020-03-24 09:20:01,483 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVDataset)...
...
```

```{note}
All the datasets used in the run have to be [thread-safe](https://www.quora.com/What-is-thread-safety-in-Python) in order for asynchronous loading/saving to work properly.
```

## Run a pipeline by name

To run the pipeline by its name, you need to add your new pipeline to the `register_pipelines()` function in `src/<package_name>/pipeline_registry.py`:

<details>
<summary><b>Click to expand</b></summary>

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
</details>

Then, from the command line, execute the following:

```bash
kedro run --pipeline=my_pipeline
```

```{note}
If you specify `kedro run` without the `--pipeline` option, it runs the `__default__` pipeline from the dictionary returned by `register_pipelines()`.
```

Further information about `kedro run` can be found in the [Kedro CLI documentation](../development/commands_reference.md#run-the-project).

## Run pipelines with IO

The above definition of pipelines only applies for non-stateful or "pure" pipelines that do not interact with the outside world. In practice, we would like to interact with APIs, databases, files and other sources of data. By combining IO and pipelines, we can tackle these more complex use cases.

By using `DataCatalog` from the IO module we are still able to write pure functions that work with our data and outsource file saving and loading to `DataCatalog`.

Through `DataCatalog`, we can control where inputs are loaded from, where intermediate variables get persisted and ultimately the location to which output variables are written.

In a simple example, we define a `MemoryDataset` called `xs` to store our inputs, save our input list `[1, 2, 3]` into `xs`, then instantiate `SequentialRunner` and call its `run` method with the pipeline and data catalog instances:

<details>
<summary><b>Click to expand</b></summary>


```python
io = DataCatalog(dict(xs=MemoryDataset()))
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
</details>



## Output to a file

We can also use IO to save outputs to a file. In this example, we define a custom `LambdaDataset` that would serialise the output to a file locally:

<details>
<summary><b>Click to expand</b></summary>


```python
def save(value):
    with open("./data/07_model_output/variance.pickle", "wb") as f:
        pickle.dump(value, f)


def load():
    with open("./data/07_model_output/variance.pickle", "rb") as f:
        return pickle.load(f)


pickler = LambdaDataset(load=load, save=save)
io.add("v", pickler)
```
</details>

It is important to make sure that the data catalog variable name `v` matches the name `v` in the pipeline definition.

Next we can confirm that this `LambdaDataset` behaves correctly:

<details>
<summary><b>Click to expand</b></summary>

```python
io.save("v", 5)
```

```python
io.load("v")
```

`Ouput`:

```Console
Out[12]: 5
```
</details>

Finally, let's run the pipeline again now and serialise the output:

<details>
<summary><b>Click to expand</b></summary>


```python
SequentialRunner().run(pipeline, catalog=io)
```

`Ouput`:

```console
Out[13]: {}
```
</details>

The output has been persisted to a local file so we don't see it directly, but it can be retrieved from the catalog:

<details>
<summary><b>Click to expand</b></summary>


```python
io.load("v")
```

`Ouput`:

```console
Out[14]: 0.666666666666667
```

```python
try:
    os.remove("./data/07_model_output/variance.pickle")
except FileNotFoundError:
    pass
```
</details>


## Configure `kedro run` arguments

The [Kedro CLI documentation](../development/commands_reference.md#run-the-project) lists the available CLI options for `kedro run`. You can alternatively supply a configuration file that contains the arguments to `kedro run`.

Here is an example file named `config.yml`, but you can choose any name for the file:


```console
$ kedro run --config=config.yml
```

where `config.yml` is formatted as below (for example):

```yaml
run:
  tags: tag1, tag2, tag3
  pipeline: pipeline1
  parallel: true
  nodes_names: node1, node2
  env: env1
```

The syntax for the options is different when you're using the CLI compared to the configuration file. In the CLI you use dashes, for example for `kedro run --from-nodes=...`, but you have to use an underscore in the configuration file:

```yaml
run:
  from_nodes: ...
```

This is because the configuration file gets parsed by [Click](https://click.palletsprojects.com/en/8.1.x/), a Python package to handle command line interfaces. Click passes the options defined in the configuration file to a Python function. The option names need to match the argument names in that function.

Variable names and arguments in Python may only contain alpha-numeric characters and underscores, so it's not possible to have a dash in the option names when using the configuration file.

```{note}
If you provide both a configuration file and a CLI option that clashes with the configuration file, the CLI option will take precedence.
```
