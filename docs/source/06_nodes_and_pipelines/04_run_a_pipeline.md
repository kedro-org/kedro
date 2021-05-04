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

You can alternatively run the nodes within the pipeline concurrently, using a `ParallelRunner`. To do so, add a flag as follows:

```bash
kedro run --parallel
```

or

```bash
kedro run --runner=ParallelRunner
```

> *Note:* You cannot use both `--parallel` and `--runner` flags at the same time (e.g. `kedro run --parallel --runner=SequentialRunner` raises an exception).

#### Multithreading
While `ParallelRunner` uses multiprocessing, you can also run the pipeline with multithreading for concurrent execution by specifying `ThreadRunner` as follows:

```bash
kedro run --runner=ThreadRunner
```


> *Note:* `SparkDataSet` doesn't work correctly with `ParallelRunner`. To add concurrency to the pipeline with `SparkDataSet`, you must use `ThreadRunner`.
>
> For more information on how to maximise concurrency when using Kedro with PySpark, please visit our guide on [how to build a Kedro pipeline with PySpark](../11_tools_integration/01_pyspark.md).



## Custom runners

If the built-in Kedro runners do not meet your requirements, you can also define your own runner within your project. For example, you may want to add a dry runner, which lists which nodes would be run without executing them:

<details>
<summary><b>Click to expand</b></summary>

```python
# in <project-name>/src/<python_package>/runner.py
from kedro.io import AbstractDataSet, DataCatalog, MemoryDataSet
from kedro.pipeline import Pipeline
from kedro.runner.runner import AbstractRunner


class DryRunner(AbstractRunner):
    """``DryRunner`` is an ``AbstractRunner`` implementation. It can be used to list which
    nodes would be run without actually executing anything.
    """

    def create_default_data_set(self, ds_name: str) -> AbstractDataSet:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set
        Returns:
            An instance of an implementation of AbstractDataSet to be used
            for all unregistered data sets.

        """
        return MemoryDataSet()

    def _run(self, pipeline: Pipeline, catalog: DataCatalog) -> None:
        """The method implementing dry pipeline running.
        Example logs output using this implementation:

            kedro.runner.dry_runner - INFO - Actual run would execute 3 nodes:
            node3: identity([A]) -> [B]
            node2: identity([C]) -> [D]
            node1: identity([D]) -> [E]

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.

        """
        nodes = pipeline.nodes
        self._logger.info(
            "Actual run would execute %d nodes:\n%s",
            len(nodes),
            "\n".join(map(str, nodes)),
        )
```
</details>

And use it with `kedro run` through the `--runner` flag:

```console
$ kedro run --runner=src.<python_package>.runner.DryRunner
```

## Load and save asynchronously

> *Note:* `ThreadRunner` doesn't support asynchronous load-input or save-output operations.

When processing a node, both `SequentialRunner` and `ParallelRunner` perform the following steps in order:

1. Load data based on node input(s)
2. Execute node function with the input(s)
3. Save the output(s)

If a node has multiple inputs or outputs (e.g., `node(func, ["a", "b", "c"], ["d", "e", "f"])`), you can reduce load and save time by using asynchronous mode. You can enable it by passing an `--async` flag to the run command as follows:

```bash
$ kedro run --async
...
2020-03-24 09:20:01,482 - kedro.runner.sequential_runner - INFO - Asynchronous mode is enabled for loading and saving data
2020-03-24 09:20:01,483 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVDataSet)...
...
```

> *Note:* All the datasets used in the run have to be [thread-safe](https://www.quora.com/What-is-thread-safety-in-Python) in order for asynchronous loading/saving to work properly.

## Run a pipeline by name

To run the pipeline by its name, you need to add your new pipeline to `register_pipelines()` function `src/<python_package>/pipeline_registry.py` as below:

<details>
<summary><b>Click to expand</b></summary>

```python
def register_pipelines():
    """Register the project's pipelines.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.

    """

    data_engineering_pipeline = de.create_pipeline()
    data_science_pipeline = ds.create_pipeline()
    my_pipeline = Pipeline(
        [
            # your definition goes here
        ]
    )

    return {
        "de": data_engineering_pipeline,
        "my_pipeline": my_pipeline,
        "__default__": data_engineering_pipeline + data_science_pipeline,
    }
```
</details>

Then from the command line, execute the following:

```bash
kedro run --pipeline my_pipeline
```

> *Note:* If you specify `kedro run` without the `--pipeline` option, it runs the `__default__` pipeline from the dictionary returned by `register_pipelines()`.

Further information about `kedro run` can be found in the [Kedro CLI documentation](../09_development/03_commands_reference.md#run-the-project).

## Run pipelines with IO

The above definition of pipelines only applies for non-stateful or "pure" pipelines that do not interact with the outside world. In practice, we would like to interact with APIs, databases, files and other sources of data. By combining IO and pipelines, we can tackle these more complex use cases.

By using `DataCatalog` from the IO module we are still able to write pure functions that work with our data and outsource file saving and loading to `DataCatalog`.

Through `DataCatalog`, we can control where inputs are loaded from, where intermediate variables get persisted and ultimately the location to which output variables are written.

In a simple example, we define a `MemoryDataSet` called `xs` to store our inputs, save our input list `[1, 2, 3]` into `xs`, then instantiate `SequentialRunner` and call its `run` method with the pipeline and data catalog instances:

<details>
<summary><b>Click to expand</b></summary>


```python
io = DataCatalog(dict(xs=MemoryDataSet()))
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

We can also use IO to save outputs to a file. In this example, we define a custom `LambdaDataSet` that would serialise the output to a file locally:

<details>
<summary><b>Click to expand</b></summary>


```python
def save(value):
    with open("./data/07_model_output/variance.pickle", "wb") as f:
        pickle.dump(value, f)


def load():
    with open("./data/07_model_output/variance.pickle", "rb") as f:
        return pickle.load(f)


pickler = LambdaDataSet(load=load, save=save)
io.add("v", pickler)
```
</details>

It is important to make sure that the data catalog variable name `v` matches the name `v` in the pipeline definition.

Next we can confirm that this `LambdaDataSet` behaves correctly:

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
