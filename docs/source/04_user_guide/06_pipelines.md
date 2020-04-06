# Pipelines

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.
>
> In this section we introduce the concept of a pipeline.

Relevant API documentation: [Pipeline](/kedro.pipeline.Pipeline)

To benefit from Kedro's automatic dependency resolution, [nodes](./05_nodes.md#nodes) can be chained in a pipeline. A pipeline is a list of nodes that use a shared set of variables.

## Building pipelines

In the following example, we construct a simple pipeline that computes the variance of a set of numbers. In practice, pipelines can use more complicated node definitions and variables usually correspond to entire datasets:


```python
def mean(xs, n):
    return sum(xs) / n


def mean_sos(xs, n):
    return sum(x ** 2 for x in xs) / n


def variance(m, m2):
    return m2 - m * m


pipeline = Pipeline(
    [
        node(len, "xs", "n"),
        node(mean, ["xs", "n"], "m", name="mean node"),
        node(mean_sos, ["xs", "n"], "m2", name="mean sos"),
        node(variance, ["m", "m2"], "v", name="variance node"),
    ]
)
```

`describe` can be used to understand what nodes are part of the pipeline:


```python
print(pipeline.describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean node
mean sos
variance node

Outputs: v
##################################
```

### Tagging pipeline nodes

You can also tag your ``Pipeline`` by providing `tags` argument, which will tag all of the pipeline's nodes.

```python
pipeline = Pipeline(
    [node(..., name="node1"), node(..., name="node2", tags="node_tag")],
    tags="pipeline_tag",
)
```

Node `node1` will only be tagged with `pipeline_tag`, while `node2` will have both `node_tag` and `pipeline_tag`.

### Merging pipelines

You can merge multiple pipelines as shown below. Note that, in this case, `pipeline_de` and `pipeline_ds` are expanded to a list of their underlying nodes of nodes which are simply merged together:


```python
pipeline_de = Pipeline([node(len, "xs", "n"), node(mean, ["xs", "n"], "m")])

pipeline_ds = Pipeline(
    [node(mean_sos, ["xs", "n"], "m2"), node(variance, ["m", "m2"], "v")]
)

last_node = node(print, "v", None)

pipeline_all = Pipeline([pipeline_de, pipeline_ds, last_node])
print(pipeline_all.describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean([n,xs]) -> [m]
mean_sos([n,xs]) -> [m2]
variance([m,m2]) -> [v]
print([v]) -> None

Outputs: None
##################################
```

### Fetching pipeline nodes

Pipelines provide access to their nodes in a topological order for enabling custom functionality, e.g. custom visualisation of pipelines. Each node has information about its inputs and outputs:


```python
nodes = pipeline.nodes
nodes
```

`Output`:

```console
Out[5]:
[Node(len, 'xs', 'n', None),
 Node(mean, ['xs', 'n'], 'm', 'mean node'),
 Node(mean_sos, ['xs', 'n'], 'm2', 'mean sos'),
 Node(variance, ['m', 'm2'], 'v', 'variance node')]
 ```

```python
nodes[0].inputs
```

`Output`:

```console
Out[6]: ['xs']
```

## Developing modular pipelines

> *Note:* Although Kedro does not enforce the structure below, we strongly encourage following it when developing your modular pipelines. Future versions of Kedro may assume this structure, which would make your modular pipelines compatible with newer versions of Kedro.

### What are modular pipelines?

Modular pipelines allow you to develop and maintain smaller pipelines. As your Kedro project evolves and gets more sophisticated, you may find out that a single (“master”) pipeline does not fit the purpose of discoverability anymore due to its complexity. Also, it may be quite hard to port any reusable parts of the original pipeline into a different project. The solution would be to split the pipeline into several logically isolated reusable components, i.e. modular pipelines.

Modular pipelines serve the following main purposes:
* Discoverability: A modular pipeline represents a logically isolated unit of work that is much easier to develop, test and maintain
* Portability: The proposed internal structure of a modular pipeline makes it easy to copy the pipeline between projects
* Generalisability: A way to create reusable analytics code in future, depending on what you put in the modular pipeline

### How do we construct modular pipelines?

#### Structure

Modular pipelines can contain any logic that can be reused. Let's look at a generic example using:
- `src/new_kedro_project/pipelines/modular_pipeline_1` - A directory for modular pipeline 1
- `src/new_kedro_project/pipelines/modular_pipeline_2` - A directory for modular pipeline 2

Requirements for modular pipelines:
* Each modular pipeline should be placed in a Python module, like `src/new_kedro_project/pipelines/modular_pipeline_1`, and `src/new_kedro_project/pipelines` should be a Python package
* A modular pipeline must expose a function called `create_pipeline` at the top-level of its package and calling `create_pipeline` with no arguments should return an instance of a [Pipeline](/kedro.pipeline.Pipeline):

```python
import new_kedro_project.pipelines.modular_pipeline_1 as mp1

pipeline1 = mp1.create_pipeline()
```

#### Ease of use and portability

Here is a list of recommendations for developing a modular pipeline:

* A modular pipeline should include a `README.md`, with all the information regarding the execution of the pipeline for the end users
* A modular pipeline _may_ have external dependencies specified in `requirements.txt`. These dependencies are _not_ currently installed by the [`kedro install`](https://kedro.readthedocs.io/en/stable/06_resources/03_commands_reference.html#kedro-install) command, so the users of your pipeline would have to run `pip install -r src/<python_package>/pipelines/<pipeline_name>/requirements.txt`
* To ensure portability, modular pipelines should use relative imports when accessing their own objects and absolute imports otherwise. Look at an example from `src/new_kedro_project/pipelines/modular_pipeline_1/pipeline.py` below:

```python
from external_package import add  # importing from external package
from kedro.pipeline import node, Pipeline

from .nodes import node1_func, node2_func  # importing its own node functions


def create_pipeline():
    node1 = node(func=node1_func, inputs="a", outputs="b")
    node2 = node(func=node2_func, inputs="c", outputs="d")
    node3 = node(func=add, inputs=["b", "d"], outputs="sum")
    return Pipeline([node1, node2, node3])
```

* Modular pipelines should _not_ depend on the main Python package (`new_kedro_project` in this example) as it would break the portability to another project
* Modular pipelines should be stitched together in a master (or `__default__`) pipeline located in `src/new_kedro_project/pipeline.py`. In our example, this pipeline combines `modular_pipeline_1` and `modular_pipeline_2`.
* Master pipeline should import and instantiate modular pipelines as shown in this example from `src/new_kedro_project/pipeline.py`:

```python
from typing import Dict

from kedro.pipeline import Pipeline

from new_kedro_project.pipelines import (
    modular_pipeline_1 as mp1,
    modular_pipeline_2 as mp2,
)


def create_pipelines(**kwargs) -> Dict[str, Pipeline]:
    pipeline1 = mp1.create_pipeline()
    pipeline2 = mp2.create_pipeline()
    pipeline_all = pipeline_1 + pipeline_2
    return {"mp1": pipeline_1, "mp2": pipeline_2, "__default__": pipeline_all}
```

> *Note:* To find out how you can run a pipeline by its name, please navigate to [this section](#running-a-pipeline-by-name).


### A modular pipeline example template

Linking all of these concepts together, here is an example of a modular pipeline structure which combines all of these concepts within a Kedro project:

* The modular pipelines:
  - `src/new_kedro_project/pipelines/data_engineering` - A pipeline that imputes missing data and discovers outlier data points
  - `src/new_kedro_project/pipelines/feature_engineering` - A pipeline that generates temporal features while aggregating data and performs a train/test split on the data
  - `src/new_kedro_project/pipelines/modelling` - A pipeline that fits models, does hyperparameter search and reports on model performance
* A master (or `__default__`) pipeline:
  - `src/new_kedro_project/pipeline.py` - combines 3 modular pipelines from the above

```console
new-kedro-project
├── .ipython/
├── conf/
├── data/
├── docs/
├── logs/
├── notebooks/
├── src
│   ├── new_kedro_project
│   │   ├── pipelines
│   │   │   ├── data_engineering
│   │   │   │   ├── __init__.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── README.md
│   │   │   ├── feature_engineering
│   │   │   │   ├── __init__.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── README.md
│   │   │   ├── modelling
│   │   │   │   ├── __init__.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── README.md
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── nodes.py
│   │   ├── pipeline.py
│   │   └── run.py
│   ├── tests
│   │   ├── __init__.py
│   │   └── test_run.py
│   ├── requirements.txt
│   └── setup.py
├── .kedro.yml
├── README.md
├── kedro_cli.py
└── setup.cfg
```

### Configuration

Nested configuration in modular pipelines is _not_ currently supported by Kedro. It means that putting config files (like `catalog.yml`) in `src/<python_package>/pipelines/<pipeline_name>/conf` will have no effect on Kedro project configuration.

The recommended way to apply the changes to project catalog or any other project configuration is to document those changes in the `README.md` of your modular pipeline. For example, you may instruct the users to copy `catalog.yml` into their top-level configuration like that:

```bash
mkdir -p conf/base/pipelines/data_engineering  # create a separate folder for the pipeline configs
cp -r src/<python_package>/pipelines/data_engineering/conf/* conf/base/pipelines/data_engineering  # copy the pipeline configs
```

### Datasets

It is important to keep in mind that Kedro resolves node execution order based on their input and output datasets. For example, if node 1 outputs the dataset `A`, and node 2 requires the dataset `A` as an input, node 1 is guaranteed to be executed before node 2 when Kedro runs the pipeline.

As a modular pipeline developer, you may not know how your pipeline will be integrated in the downstream projects and what data catalog configuration they may have. Therefore, it is crucial to make it clear in the pipeline documentation what datasets (names and types) are required as inputs by your modular pipeline and what datasets it produces as outputs.

## Connecting existing pipelines

When two existing pipelines need to work together, they should be connected by the datasets.
But the names might be different, requiring manual fixes to be applied to the pipeline itself.
Alternative solution would be to `transform` an existing pipeline. Consider this example:

```python
cook_pipeline = Pipeline(
    [node(defrost, "frozen_meat", "meat"), node(grill, "meat", "grilled_meat"),]
)

lunch_pipeline = Pipeline([node(eat, "food", None),])
```

A simple `cook_pipeline + lunch_pipeline` doesn't work, `food` input needs to be mapped to `grilled_meat` output.
That's how it can be done, all three resulting pipelines do the job equally fine:

```python
final_pipeline1 = (
    cook_pipeline.transform(datasets={"grilled_meat": "food"}) + lunch_pipeline
)
final_pipeline2 = cook_pipeline + lunch_pipeline.transform(
    datasets={"food": "grilled_meat"}
)
final_pipeline3 = cook_pipeline.transform(
    datasets={"grilled_meat": "new_name"}
) + lunch_pipeline.transform(datasets={"food": "new_name"})
```

Note that `Pipeline.transform()` will skip prefixing when node inputs and outputs contain parameter references (`params:` and `parameters`).
Example:
```python
transformed_pipeline = Pipeline(
    [node(node_func, ["input", "params:x"], None)]
).transform(prefix="new")
# `transformed_pipeline` will be `Pipeline([node(node_func, ["new.input", "params:x"], None)])`
```

## Using a modular pipeline twice
Consider the example:

```python
cook_pipeline = Pipeline(
    [
        node(defrost, "frozen_meat", "meat", name="defrost_node"),
        node(grill, "meat", "grilled_meat"),
    ]
)

breakfast_pipeline = Pipeline([node(eat_breakfast, "breakfast_food", None),])
lunch_pipeline = Pipeline([node(eat_lunch, "lunch_food", None),])
```
Now we need to "defrost" two different types of food and feed it to different pipelines.
But we can't use the `cook_pipeline` twice, the internal dataset names will conflict.
We might try to call `transform` and rename all datasets,
but the conflicting explicitly set `name="defrost_node"` remains.

The right solution is:
```python
pipeline = (
    cook_pipeline.transform(
        datasets={"grilled_meat": "breakfast_food"}, prefix="breakfast"
    )
    + breakfast_pipeline
    + cook_pipeline.transform(datasets={"grilled_meat": "lunch_food"}, prefix="lunch")
    + lunch_pipeline
)
```
`prefix="lunch"` renames all datasets and nodes, prefixing them with `"lunch."`,
except those datasets that we rename explicitly (`grilled_meat`).

The resulting pipeline now has two separate nodes, `breakfast.defrost_node` and
`lunch.defrost_node`. Also two separate datasets `breakfast.meat` and `lunch.meat`
connect the nodes inside the pipelines, causing no confusion between them.

## Bad pipelines

As you notice, pipelines can usually readily resolve their dependencies. In some cases, resolution is not possible and pipelines are not well-formed.

### Pipeline with bad nodes

In this case we have a pipeline consisting of a single node with no input and output:


```python
try:
    Pipeline([node(lambda: print("!"), None, None)])
except Exception as e:
    print(e)
```

`Output`:

```console
Invalid Node definition: it must have some `inputs` or `outputs`.
Format should be: node(function, inputs, outputs)
```

### Pipeline with circular dependencies

For every two variables where the first depends on the second, there must not be a way in which the second also depends on the first, otherwise, a circular dependency will prevent us from compiling the pipeline.

The first node captures the relationship of how to calculate `y` from `x` and the second captures the relationship of how to calculate `x` knowing `y`. Both cannot coexist in the same pipeline:

```python
try:
    Pipeline(
        [
            node(lambda x: x + 1, "x", "y", name="first node"),
            node(lambda y: y - 1, "y", "x", name="second node"),
        ]
    )
except Exception as e:
    print(e)
```

`Output`:

```console
Circular dependencies exist among these items: ['first node: <lambda>([x]) -> [y]', 'second node: <lambda>([y]) -> [x]']
```

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

> *Note:* You cannot use both `--parallel` and `--runner` flags at the same time (e.g. `kedro run --parallel --runner=SequentialRunner` raises an exception).

### Running a pipeline by name

To run the pipeline by its name, you need to add your new pipeline to `create_pipelines()` function `src/<python_package>/pipeline.py` as below:

```python
def create_pipelines(**kwargs):
    """Create the project's pipeline.

    Args:
        kwargs: Ignore any additional arguments added in the future.

    Returns:
        Pipeline: The resulting pipeline.

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

Then from the command line, execute the following:

```bash
kedro run --pipeline my_pipeline
```

> *Note:* `kedro run` without `--pipeline` option runs `__default__` pipeline from the dictionary returned by `create_pipelines()`.

### Modifying a `kedro run`

Kedro has options to modify pipeline runs. Here is a list of CLI arguments supported out of the box:

```eval_rst
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| CLI command                                                  | Description                                                                     | Multiple options allowed? |
+==============================================================+=================================================================================+===========================+
| :code:`kedro run --pipeline de`                              | Run the whole pipeline by its name                                              | No                        |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --node debug_me,debug_me_too`               | Run only nodes with specified names                                             | Yes                       |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --from-nodes node1,node2`                   | A list of node names which should be used as a starting point                   | No                        |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --to-nodes node3,node4`                     | A list of node names which should be used as an end point                       | No                        |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --from-inputs dataset1,dataset2`            | A list of dataset names which should be used as a starting point                | No                        |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --tag some_tag1,some_tag2`                  | Run only nodes which have any of these tags attached                            | Yes                       |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --params param_key1:value1,param_key2:2.0`  | Does a parametrised kedro run with {"param_key1": "value1", "param_key2": 2}    | Yes                       |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --env env_name`                             | Run the pipeline in the env_name environment. Defaults to local if not provided | No                        |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
| :code:`kedro run --config config.yml`                        | Specify all command line options in a configuration file called config.yml      | No                        |
+--------------------------------------------------------------+---------------------------------------------------------------------------------+---------------------------+
```

You can also combine these options together, so the command `kedro run --from-nodes split --to-nodes predict, report` will run all the nodes from `split` to `predict` and `report`. And this functionality is extended to the `kedro run --config config.yml` command which allows you to [specify run commands in a configuration file](./03_configuration.md#configuring-kedro-run-arguments). And note, a parameterized run is best used for dynamic parameters, i.e. running the same pipeline with different inputs, for static parameters that do not change we recommend following this [methodology](./03_configuration.md#parameters).


### Applying decorators on pipelines

You can apply decorators on whole pipelines, the same way you apply decorators on single nodes. For example, if you want to apply the decorators defined in the earlier section to all pipeline nodes simultaneously, you can do so as follows:

```python
hello_pipeline = Pipeline(
    [node(say_hello, "name1", None), node(say_hello, "name2", None)]
).decorate(apply_g, apply_h)

SequentialRunner().run(
    hello_pipeline, DataCatalog({}, dict(name1="Kedro", name2="Python"))
)
```

`Output`:

```console
Hello f(h(g(Kedro)))!
Hello f(h(g(Python)))!
Out[9]: {}
```

Decorators can be useful for monitoring your pipeline. Kedro currently has 1 built-in decorator: `log_time`, which will log the time taken for executing your node. You can find it in `kedro.pipeline.decorators`. Other decorators can be found in `kedro.contrib.decorators`, for which you will need to install the required dependencies.

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

## Partial pipelines

Sometimes it is desirable to work with only a subset of a pipeline's nodes. Let's look at the example pipeline we created earlier:

```python
print(pipeline.describe())
```

`Ouput`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean node
mean sos
variance node

Outputs: v
##################################
```

#### Partial pipeline starting from inputs
One way to specify a partial pipeline is by providing a set of pre-calculated inputs which should serve as a start of the partial pipeline. For example, in order to fetch the partial pipeline running from input `m2` downstream you can specify it like this:

```python
print(pipeline.from_inputs("m2").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: m, m2

variance node

Outputs: v
##################################
```

Specifying that the partial pipeline from inputs `m` and `xs` is needed will result in the following pipeline:

```python
print(pipeline.from_inputs("m", "xs").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean node
mean sos
variance node

Outputs: v
##################################
```

As it can been seen from the pipeline description, adding `m` in the `from_inputs` list does not guarantee that it will not be recomputed if another provided input like `xs` forces recomputing it.

#### Partial pipeline starting from nodes
Another way of selecting a partial pipeline is by specifying the nodes which should be used as a start of the new pipeline. For example you can do as follows:

```python
print(pipeline.from_nodes("mean node").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: m2, n, xs

mean node
variance node

Outputs: v
##################################
```

As you can see, this will create a partial pipeline starting from the specified node and continuing to all other nodes downstream.

You can run the resulting partial pipeline by running the following command in your terminal window:

```bash
kedro run --from-nodes="mean node"
```

#### Partial pipeline ending at nodes
Similarly, you can specify the nodes which should be used as an end of the new pipeline. For example, you can do as follows:

```python
print(pipeline.to_nodes("mean node").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean node

Outputs: m
##################################
```

As you can see, this will create a partial pipeline starting at the top and ending with the specified node.

You can run the resulting partial pipeline by running the following command in your terminal window:

```bash
kedro run --to-nodes="mean node"
```

Furthermore, you can combine these two flags to specify a range of nodes to be included in the new pipeline. This would look like:

```bash
kedro run --from-nodes A --to-nodes Z
```

or, when specifying multiple nodes:
```bash
kedro run --from-nodes A,D --to-nodes X,Y,Z
```

#### Partial pipeline from nodes with tags
One can also create a partial pipeline from the nodes that have specific tags attached to them. In order to construct a partial pipeline out of nodes that have both tag `t1` *AND* tag `t2`, you can run the following:

```python
print(pipeline.only_nodes_with_tags("t1", "t2").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: None

Outputs: None
##################################
```

To construct a partial pipeline out of nodes that have tag `t1` *OR* tag `t2`, please execute the following:

```python
partial_pipeline = pipeline.only_nodes_with_tags("t1") + pipeline.only_nodes_with_tags(
    "t2"
)
print(partial_pipeline.describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: None

Outputs: None
##################################
```

#### Running only some nodes
Sometimes you might need to run only some of the nodes in a pipeline. To do that, you can do as follows:

```python
print(pipeline.only_nodes("mean node", "mean sos").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: n, xs

mean node
mean sos

Outputs: m, m2
##################################
```

This will create a partial pipeline, consisting solely of the nodes you specify as arguments in the method call.

You can check this out for yourself by updating the definition of the first node in the example code provided in `pipeline.py` as follows:

```python
node(
    split_data,
    ["example_iris_data", "parameters"],
    dict(
        train_x="example_train_x",
        train_y="example_train_y",
        test_x="example_test_x",
        test_y="example_test_y",
    ),
    name="node1",
),
```

and then run the following command in your terminal window:

```bash
kedro run --node=node1
```

You may specify multiple names like so:

```bash
kedro run --node=node1,node2
```

> *Note:* The run will only succeed if all the inputs required by those nodes already exist, i.e. already produced or present in the data catalog.


#### Recreating Missing Outputs

Kedro supports the automatic generation of partial pipelines that take into account existing node outputs. This can be helpful to avoid re-running nodes that take a long time:

```python
print(pipeline.describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean node
mean sos
variance node

Outputs: v
##################################
```

To demonstrate this, let us save the intermediate output `n` using a `JSONLocalDataSet`.

```python
n_json = JSONLocalDataSet(filepath="./data/07_model_output/len.json")
io = DataCatalog(dict(xs=MemoryDataSet([1, 2, 3]), n=n_json))
```

Because `n` was not saved previously, checking for its existence returns `False`:

```python
io.exists("n")
```

`Output`:

```console
Out[15]: False
```

Running the pipeline calculates `n` and saves the result to disk:

```python
SequentialRunner().run(pipeline, io)
```

`Output`:

```console
Out[16]: {'v': 0.666666666666667}
```

```python
io.exists("n")
```

`Output`:

```console
Out[17]: True
```


We can avoid re-calculating `n` (and all other results that have already been saved) by using the `Runner.run_only_missing` method. Note that the first node of the original pipeline (`len([xs]) -> [n]`) has been removed:

```python
SequentialRunner().run_only_missing(pipeline, io)
```

`Ouput`:

```console
Out[18]: {'v': 0.666666666666667}
```

```python
try:
    os.remove("./data/07_model_output/len.json")
except FileNotFoundError:
    pass
```
