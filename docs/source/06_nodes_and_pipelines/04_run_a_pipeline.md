## Running pipelines

When running pipelines, it can be useful to check the inputs and outputs of a pipeline:

```python
pipeline.inputs()
```

`Output`:

```console
Out[7]: {'xs'}
```

```python
pipeline.outputs()
```

`Output`:

```console
Out[8]: {'v'}
```

### Runners

Runners are different execution mechanisms for running pipelines. They all inherit from `AbstractRunner`. You can use `SequentialRunner` to execute pipeline nodes one-by-one based on their dependencies.

We recommend using `SequentialRunner` in cases where:

- the pipeline has limited branching
- the pipeline is fast
- the resource consuming steps require most of a scarce resource (e.g., significant RAM, disk memory or CPU)

Now we can execute the pipeline by providing a runner and values for each of the inputs.

From the command line, you can run the pipeline as follows:

```bash
kedro run
```
<details>
<summary><b>Click to expand</b></summary>

`Output`:

```console

2019-04-26 17:19:01,341 - root - INFO - ** Kedro project new-kedro-project
2019-04-26 17:19:01,360 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVLocalDataSet)...
2019-04-26 17:19:01,387 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:19:01,387 - kedro.pipeline.node - INFO - Running node: split_data([example_iris_data,params:example_test_data_ratio]) -> [example_test_x,example_test_y,example_train_x,example_train_y]
2019-04-26 17:19:01,437 - kedro.io.data_catalog - INFO - Saving data to `example_test_x` (MemoryDataSet)...
2019-04-26 17:19:01,439 - kedro.io.data_catalog - INFO - Saving data to `example_train_y` (MemoryDataSet)...
2019-04-26 17:19:01,443 - kedro.io.data_catalog - INFO - Saving data to `example_train_x` (MemoryDataSet)...
2019-04-26 17:19:01,447 - kedro.io.data_catalog - INFO - Saving data to `example_test_y` (MemoryDataSet)...
2019-04-26 17:19:01,447 - kedro.runner.sequential_runner - INFO - Completed 1 out of 4 tasks
2019-04-26 17:19:01,448 - kedro.io.data_catalog - INFO - Loading data from `example_train_x` (MemoryDataSet)...
2019-04-26 17:19:01,454 - kedro.io.data_catalog - INFO - Loading data from `example_train_y` (MemoryDataSet)...
2019-04-26 17:19:01,461 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:19:01,461 - kedro.pipeline.node - INFO - Running node: train_model([example_train_x,example_train_y,parameters]) -> [example_model]
2019-04-26 17:19:01,887 - kedro.io.data_catalog - INFO - Saving data to `example_model` (MemoryDataSet)...
2019-04-26 17:19:01,887 - kedro.runner.sequential_runner - INFO - Completed 2 out of 4 tasks
2019-04-26 17:19:01,888 - kedro.io.data_catalog - INFO - Loading data from `example_test_x` (MemoryDataSet)...
2019-04-26 17:19:01,888 - kedro.io.data_catalog - INFO - Loading data from `example_model` (MemoryDataSet)...
2019-04-26 17:19:01,888 - kedro.pipeline.node - INFO - Running node: predict([example_model,example_test_x]) -> [example_predictions]
2019-04-26 17:19:01,890 - kedro.io.data_catalog - INFO - Saving data to `example_predictions` (MemoryDataSet)...
2019-04-26 17:19:01,891 - kedro.runner.sequential_runner - INFO - Completed 3 out of 4 tasks
2019-04-26 17:19:01,891 - kedro.io.data_catalog - INFO - Loading data from `example_predictions` (MemoryDataSet)...
2019-04-26 17:19:01,891 - kedro.io.data_catalog - INFO - Loading data from `example_test_y` (MemoryDataSet)...
2019-04-26 17:19:01,891 - kedro.pipeline.node - INFO - Running node: report_accuracy([example_predictions,example_test_y]) -> None
2019-04-26 17:19:01,892 - new_kedro_project.nodes.example - INFO - Model accuracy on test set: 96.67%
2019-04-26 17:19:01,892 - kedro.runner.sequential_runner - INFO - Completed 4 out of 4 tasks
2019-04-26 17:19:01,892 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```
</details>

which will run the pipeline using `SequentialRunner` by default. You can also explicitly use `SequentialRunner` as follows:

```bash
kedro run --runner=SequentialRunner
```

In case you want to run the pipeline using `ParallelRunner`, add a flag as follows:

```bash
kedro run --parallel
```

or

```bash
kedro run --runner=ParallelRunner
```

`Output`:

<details>
<summary><b>Click to expand</b></summary>

```console

2019-04-26 17:20:45,012 - root - INFO - ** Kedro project new-kedro-project
2019-04-26 17:20:45,081 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVLocalDataSet)...
2019-04-26 17:20:45,099 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:20:45,099 - kedro.pipeline.node - INFO - Running node: split_data([example_iris_data,params:example_test_data_ratio]) -> [example_test_x,example_test_y,example_train_x,example_train_y]
2019-04-26 17:20:45,115 - kedro.io.data_catalog - INFO - Saving data to `example_test_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,121 - kedro.io.data_catalog - INFO - Saving data to `example_test_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,123 - kedro.io.data_catalog - INFO - Saving data to `example_train_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,125 - kedro.io.data_catalog - INFO - Saving data to `example_train_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,135 - kedro.io.data_catalog - INFO - Loading data from `example_train_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,140 - kedro.io.data_catalog - INFO - Loading data from `example_train_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,142 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:20:45,142 - kedro.pipeline.node - INFO - Running node: train_model([example_train_x,example_train_y,parameters]) -> [example_model]
2019-04-26 17:20:45,437 - kedro.io.data_catalog - INFO - Saving data to `example_model` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,444 - kedro.io.data_catalog - INFO - Loading data from `example_test_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,449 - kedro.io.data_catalog - INFO - Loading data from `example_model` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,449 - kedro.pipeline.node - INFO - Running node: predict([example_model,example_test_x]) -> [example_predictions]
2019-04-26 17:20:45,451 - kedro.io.data_catalog - INFO - Saving data to `example_predictions` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,457 - kedro.io.data_catalog - INFO - Loading data from `example_predictions` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,461 - kedro.io.data_catalog - INFO - Loading data from `example_test_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,461 - kedro.pipeline.node - INFO - Running node: report_accuracy([example_predictions,example_test_y]) -> None
2019-04-26 17:20:45,466 - new_kedro_project.nodes.example - INFO - Model accuracy on test set: 100.00%
2019-04-26 17:20:45,494 - kedro.runner.parallel_runner - INFO - Pipeline execution completed successfully.
```
</details>

> *Note:* You cannot use both `--parallel` and `--runner` flags at the same time (e.g. `kedro run --parallel --runner=SequentialRunner` raises an exception).

> *Note:* `SparkDataSet` doesn't work correctly with `ParallelRunner`.

In case you want to get some sort of concurrency for the pipeline with `SparkDataSet` you can use `ThreadRunner`. It uses threading for concurrent execution whereas `ParallelRunner` uses multiprocessing. For more information on how to maximise concurrency when using Kedro with PySpark, please visit our guide on [how to build a Kedro pipeline with PySpark](../11_tools_integration/01_pyspark.md).

You should use the following command to run the pipeline using `ThreadRunner`:

```bash
kedro run --runner=ThreadRunner
```

`Output`:

<details>
<summary><b>Click to expand</b></summary>

```console
...
2020-04-07 13:29:15,934 - kedro.io.data_catalog - INFO - Loading data from `spark_data_2` (SparkDataSet)...
2020-04-07 13:29:15,934 - kedro.io.data_catalog - INFO - Loading data from `spark_data_1` (SparkDataSet)...
2020-04-07 13:29:19,256 - kedro.pipeline.node - INFO - Running node: report_accuracy([spark_data_2]) -> [spark_data_2_output]
2020-04-07 13:29:19,256 - kedro.pipeline.node - INFO - Running node: split_data([spark_data_1]) -> [spark_data_1_output]
2020-04-07 13:29:20,355 - kedro.io.data_catalog - INFO - Saving data to `spark_data_2_output` (SparkDataSet)...
2020-04-07 13:29:20,356 - kedro.io.data_catalog - INFO - Saving data to `spark_data_1_output` (SparkDataSet)...
20/04/07 13:29:20 WARN MemoryManager: Total allocation exceeds 95.00% (906,992,014 bytes) of heap memory
Scaling row group sizes to 96.54% for 7 writers
20/04/07 13:29:20 WARN MemoryManager: Total allocation exceeds 95.00% (906,992,014 bytes) of heap memory
Scaling row group sizes to 84.47% for 8 writers
20/04/07 13:29:20 WARN MemoryManager: Total allocation exceeds 95.00% (906,992,014 bytes) of heap memory
Scaling row group sizes to 96.54% for 7 writers
2020-04-07 13:29:20,840 - kedro.runner.thread_runner - INFO - Pipeline execution completed successfully.
```
</details>

> *Note:* `ThreadRunner` doesn't support [asynchronous inputs loading and outputs saving](#asynchronous-loading-and-saving).

#### Using a custom runner

If the built-in runners do not meet your requirements, you can define your own runner in your project instead. For example, you may want to add a dry runner, which lists which nodes would be run instead of executing them. You can define it in the following way:

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

### Asynchronous loading and saving
When processing a node, both `SequentialRunner` and `ParallelRunner` perform the following steps in order:

1. Load data based on node input(s)
2. Execute node function with the input(s)
3. Save the output(s)

If a node has multiple inputs or outputs (e.g., `node(func, ["a", "b", "c"], ["d", "e", "f"])`), you can reduce load and save time by using asynchronous mode. You can enable it by passing an extra boolean flag to the runner's constructor in `src/<project-package>/run.py` as follows:

```python
from kedro.runner import SequentialRunner

class ProjectContext(KedroContext):
    def run(self, *args, **kwargs):
        kwargs["runner"] = SequentialRunner(is_async=True)
        # or ParallelRunner(is_async=True). By default, `is_async` is False.
        return super().run(*args, **kwargs)
```

Once you enabled the asynchronous mode and ran `kedro run` from the command line, you should see the following logging message:

```bash
...
2020-03-24 09:20:01,482 - kedro.runner.sequential_runner - INFO - Asynchronous mode is enabled for loading and saving data
2020-03-24 09:20:01,483 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVDataSet)...
...
```

> *Note:* All the datasets used in the run have to be [thread-safe](https://www.quora.com/What-is-thread-safety-in-Python) in order for asynchronous loading/saving to work properly.

### Running a pipeline by name

To run the pipeline by its name, you need to add your new pipeline to `register_pipelines()` function `src/<python_package>/hooks.py` as below:

<details>
<summary><b>Click to expand</b></summary>

```python
from kedro.framework.hooks import hook_impl


class ProjectHooks:

    @hook_impl
    def register_pipelines(self):
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


project_hooks = ProjectHooks()
```
</details>

Then from the command line, execute the following:

```bash
kedro run --pipeline my_pipeline
```

> *Note:* `kedro run` without `--pipeline` option runs `__default__` pipeline from the dictionary returned by `register_pipelines()`.

Further information about `kedro run` can be found in the [Kedro CLI documentation](../09_development/03_commands_reference.md#run-the-project).

## Running pipelines with IO

The above definition of pipelines only applies for non-stateful or "pure" pipelines that do not interact with the outside world. In practice, we would like to interact with APIs, databases, files and other sources of data. By combining IO and pipelines, we can tackle these more complex use cases.

By using `DataCatalog` from the IO module we are still able to write pure functions that work with our data and outsource file saving and loading to `DataCatalog`.

Through `DataCatalog`, we can control where inputs are loaded from, where intermediate variables get persisted and ultimately the location to which output variables are written:

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

In this simple example, we defined a `MemoryDataSet` called `xs` to store our inputs, saved our input list `[1, 2, 3]` into `xs`, then instantiated `SequentialRunner` and called its `run` method with the pipeline and data catalog instances.

## Outputting to a file

We can also use IO to save outputs to a file. In this example, we define a custom LambdaDataSet that would serialise the output to a file locally:

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

It is important to make sure that the data catalog variable name `v` matches the name `v` in the pipeline definition.

Next we can confirm that this `LambdaDataSet` works:

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

Finally, let's run the pipeline again now serialising the output:

```python
SequentialRunner().run(pipeline, catalog=io)
```

`Ouput`:

```console
Out[13]: {}
```

Because the output has been persisted to a local file we don't see it directly, but it can be retrieved from the catalog:

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
