# Nodes and pipelines

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.
In this section we introduce pipelines and nodes.

Relevant API documentation:
* [`Pipeline`](/kedro.pipeline.Pipeline)
* [`node`](/kedro.pipeline.node)

To run the code snippets demonstrated below for yourself, you will first need to import some Kedro and standard libraries.

```python
from kedro.pipeline import *
from kedro.io import *
from kedro.runner import *

import pickle
import os
```
## Nodes

Nodes are used to coordinate complex, dependent tasks. Pipelines are flexible and are used to combine nodes reproducibly to build simple machine learning workflows or even build entire end-to-end production workflows.

## Creating a pipeline node

A node is created by specifying a function, input variable names and output variable names. Let's consider a simple function that adds two numbers:

```python
def add(x, y):
    return x + y
```

The add function has two inputs `x` and `y` and a single output. A new node can now be created with this function:

```python
adder_node = node(func=add, inputs=['a', 'b'], outputs='sum')
adder_node
```

`Output`:

```console
Out[1]: Node(add, ['a', 'b'], 'sum', None)
```

You can also add labels to nodes which will be used to describe them in logs:

```python
adder_node = node(func=add, inputs=['a', 'b'], outputs='sum')
print(str(adder_node))

adder_node = node(func=add, inputs=['a', 'b'], outputs='sum', name='adding_a_and_b')
print(str(adder_node))
```

`Output`:

```console
add([a,b]) -> [sum]
adding_a_and_b: add([a,b]) -> [sum]
```

Let's break down the node definition:

* `add` is our function that will execute when running the node
* `['a', 'b']` specify our input variable names. Note that in this case, they are different from `x` and `y`
* `sum` specifies the name of our return variable. The value returned by `add` will be bound in this variable
* `name` is an optional label, which can be used to provide description of the business logic of the node

### Node definition syntax

There is a special syntax for describing function inputs and outputs. This allows different Python functions to be reused in nodes and supports dependency resolution in pipelines.

### Syntax for input variables

```eval_rst
+----------------------------------+-----------------+-----------------------------+---------------------------------------+
| Input syntax                     | Meaning         | Example function parameters | How function is called when node runs |
+==================================+=================+=============================+=======================================+
| :code:`None`                     | No input        | :code:`def f()`             | :code:`f()`                           |
+----------------------------------+-----------------+-----------------------------+---------------------------------------+
| :code:`'a'`                      | Single input    | :code:`def f(arg1)`         | :code:`f(a)`                          |
+----------------------------------+-----------------+-----------------------------+---------------------------------------+
| :code:`['a', 'b']`               | Multiple inputs | :code:`def f(arg1, arg2)`   | :code:`f(a, b)`                       |
+----------------------------------+-----------------+-----------------------------+---------------------------------------+
| :code:`dict(arg1='x', arg2='y')` | Keyword inputs  | :code:`def f(arg1, arg2)`   | :code:`f(arg1='x', arg2='y')`         |
+----------------------------------+-----------------+-----------------------------+---------------------------------------+
```

### Syntax for output variables

```eval_rst
+----------------------------------+-------------------+-------------------------------------+
| Output syntax                    | Meaning           | Example return statement            |
+==================================+===================+=====================================+
| :code:`None`                     | No output         | Does not return                     |
+----------------------------------+-------------------+-------------------------------------+
| :code:`'a'`                      | Single output     | :code:`return a`                    |
+----------------------------------+-------------------+-------------------------------------+
| :code:`['a', 'b']`               | List output       | :code:`return [a, b]`               |
+----------------------------------+-------------------+-------------------------------------+
| :code:`dict(key1='a', key2='b')` | Dictionary output | :code:`return dict(key1=a, key2=b)` |
+----------------------------------+-------------------+-------------------------------------+
```

Any combinations of the above are possible, except nodes of the form `node(f, None, None)` (at least a single input or output needs to be provided).

## Running nodes

To run a node, you need to instantiate its inputs. In this case, the node expects two inputs:

```python
adder_node.run(dict(a=2, b=3))
```

`Output`:

```console
Out[2]: {'sum': 5}
```

### Applying decorators to nodes

For computations that need to run before and after node execution, Kedro is compatible with Python decorators. Below are example decorators that modify the first string argument of a given function:


```python
from functools import wraps
from typing import Callable


def apply_f(func: Callable) -> Callable:
    @wraps(func)
    def with_f(*args, **kwargs):
        return func(*["f({})".format(a) for a in args], **kwargs)
    return with_f


def apply_g(func: Callable) -> Callable:
    @wraps(func)
    def with_g(*args, **kwargs):
        return func(*["g({})".format(a) for a in args], **kwargs)
    return with_g


def apply_h(func: Callable) -> Callable:
    @wraps(func)
    def with_h(*args, **kwargs):
        return func(*["h({})".format(a) for a in args], **kwargs)
    return with_h
```

So if you want to create a function and make sure that `apply_f` is applied to every call of your function, including in Kedro nodes, you can do as follows:

```python
@apply_f
def say_hello(name):
    print("Hello {}!".format(name))


hello_node = node(say_hello, 'name', None)
hello_node.run(dict(name="Kedro"))
```

`Output`:

```console
In [3]: hello_node.run(dict(name="Kedro"))
Hello f(Kedro)!
Out[3]: {}
```

If you want to apply an additional decorator to the same function, but just for another node:

```python
hello_node_wrapped = node(apply_g(say_hello), 'name', None)

hello_node.run(dict(name="Kedro"))
hello_node_wrapped.run(dict(name="Kedro"))
```

`Output`:

```console
Hello f(Kedro)!
Hello f(g(Kedro))!
Out[4]: {}
```

### Applying multiple decorators to nodes

You can also provide a list of decorators as shown here:

```python
hello_wrapped = node(apply_g(apply_h(say_hello)), 'name', None)
hello_decorated = hello_node.decorate(apply_g, apply_h)

hello_wrapped.run(dict(name="Kedro"))
hello_decorated.run(dict(name="Kedro"))
```

`Output`:

```console
Hello f(h(g(Kedro)))!
Hello f(h(g(Kedro)))!
```

Kedro comes with a few built-in decorators which are very useful when building your pipeline. You can learn more how to apply decorators to whole pipelines and the list of built-in decorators in [a separate section below](./05_nodes_and_pipelines.md#applying-decorators-on-pipelines).

## Building pipelines

To benefit from Kedro's automatic dependency resolution, nodes can be chained in a pipeline. A pipeline is a list of nodes that use a shared set of variables.

In the following example, we construct a simple pipeline that computes the variance of a set of numbers. In practice, pipelines can use more complicated node definitions and variables usually correspond to entire datasets:


```python
def mean(xs, n):
    return sum(xs) / n


def mean_sos(xs, n):
    return sum(x*x for x in xs) / n


def variance(m, m2):
    return m2 - m * m


pipeline = Pipeline([
    node(len, 'xs', 'n'),
    node(mean, ['xs', 'n'], 'm', name='mean node'),
    node(mean_sos, ['xs', 'n'], 'm2', name='mean sos'),
    node(variance, ['m', 'm2'], 'v', name='variance node')
])
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

### Merging pipelines

You can merge multiple pipelines as shown below. Note that, in this case, `pipeline_de` and `pipeline_ds` are expanded to a list of their underlying nodes of nodes which are simply merged together:


```python
pipeline_de = Pipeline([
    node(len, 'xs', 'n'),
    node(mean, ['xs', 'n'], 'm')
])

pipeline_ds = Pipeline([
    node(mean_sos, ['xs', 'n'], 'm2'),
    node(variance, ['m', 'm2'], 'v')
])

last_node = node(print, 'v', None)

pipeline_all = Pipeline([
    pipeline_de,
    pipeline_ds,
    last_node
])
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

## Bad pipelines

As you notice, pipelines can usually readily resolve their dependencies. In some cases, resolution is not possible and pipelines are not well-formed.

### Pipeline with bad nodes

In this case we have a pipeline consisting of a single node with no input and output:


```python
try:
    Pipeline([
        node(lambda: print('!'), None, None)
    ])
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
    Pipeline([
        node(lambda x: x+1, 'x', 'y', name='first node'),
        node(lambda y: y-1, 'y', 'x', name='second node')
    ])
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
- `PySpark` is being used


Now we can execute the pipeline by providing a runner and values for each of the inputs.

From the command line, you can run the pipeline as follows:

```bash
kedro run
```

`Output`:

```console
2019-04-26 17:19:01,341 - root - INFO - ** Kedro project new-kedro-project
2019-04-26 17:19:01,343 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/logging.yml
2019-04-26 17:19:01,349 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/catalog.yml
2019-04-26 17:19:01,351 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/credentials.yml
2019-04-26 17:19:01,352 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/parameters.yml
2019-04-26 17:19:01,360 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVLocalDataSet)...
2019-04-26 17:19:01,387 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:19:01,437 - kedro.io.data_catalog - INFO - Saving data to `example_test_x` (MemoryDataSet)...
2019-04-26 17:19:01,439 - kedro.io.data_catalog - INFO - Saving data to `example_train_y` (MemoryDataSet)...
2019-04-26 17:19:01,443 - kedro.io.data_catalog - INFO - Saving data to `example_train_x` (MemoryDataSet)...
2019-04-26 17:19:01,447 - kedro.io.data_catalog - INFO - Saving data to `example_test_y` (MemoryDataSet)...
2019-04-26 17:19:01,447 - kedro.runner.sequential_runner - INFO - Completed 1 out of 4 tasks
2019-04-26 17:19:01,448 - kedro.io.data_catalog - INFO - Loading data from `example_train_x` (MemoryDataSet)...
2019-04-26 17:19:01,454 - kedro.io.data_catalog - INFO - Loading data from `example_train_y` (MemoryDataSet)...
2019-04-26 17:19:01,461 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:19:01,887 - kedro.io.data_catalog - INFO - Saving data to `example_model` (MemoryDataSet)...
2019-04-26 17:19:01,887 - kedro.runner.sequential_runner - INFO - Completed 2 out of 4 tasks
2019-04-26 17:19:01,888 - kedro.io.data_catalog - INFO - Loading data from `example_test_x` (MemoryDataSet)...
2019-04-26 17:19:01,888 - kedro.io.data_catalog - INFO - Loading data from `example_model` (MemoryDataSet)...
2019-04-26 17:19:01,890 - kedro.io.data_catalog - INFO - Saving data to `example_predictions` (MemoryDataSet)...
2019-04-26 17:19:01,891 - kedro.runner.sequential_runner - INFO - Completed 3 out of 4 tasks
2019-04-26 17:19:01,891 - kedro.io.data_catalog - INFO - Loading data from `example_predictions` (MemoryDataSet)...
2019-04-26 17:19:01,891 - kedro.io.data_catalog - INFO - Loading data from `example_test_y` (MemoryDataSet)...
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
2019-04-26 17:20:45,012 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/logging.yml
2019-04-26 17:20:45,014 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/catalog.yml
2019-04-26 17:20:45,016 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/credentials.yml
2019-04-26 17:20:45,016 - anyconfig - INFO - Loading: /private/tmp/new-kedro-project/conf/base/parameters.yml
2019-04-26 17:20:45,081 - kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVLocalDataSet)...
2019-04-26 17:20:45,099 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:20:45,115 - kedro.io.data_catalog - INFO - Saving data to `example_test_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,121 - kedro.io.data_catalog - INFO - Saving data to `example_test_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,123 - kedro.io.data_catalog - INFO - Saving data to `example_train_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,125 - kedro.io.data_catalog - INFO - Saving data to `example_train_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,135 - kedro.io.data_catalog - INFO - Loading data from `example_train_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,140 - kedro.io.data_catalog - INFO - Loading data from `example_train_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,142 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-04-26 17:20:45,437 - kedro.io.data_catalog - INFO - Saving data to `example_model` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,444 - kedro.io.data_catalog - INFO - Loading data from `example_test_x` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,449 - kedro.io.data_catalog - INFO - Loading data from `example_model` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,451 - kedro.io.data_catalog - INFO - Saving data to `example_predictions` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,457 - kedro.io.data_catalog - INFO - Loading data from `example_predictions` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,461 - kedro.io.data_catalog - INFO - Loading data from `example_test_y` (AutoProxy[MemoryDataSet])...
2019-04-26 17:20:45,466 - new_kedro_project.nodes.example - INFO - Model accuracy on test set: 100.00%
2019-04-26 17:20:45,494 - kedro.runner.parallel_runner - INFO - Pipeline execution completed successfully.
```

> *Note:* You cannot use both `--parallel` and `--runner` flags at the same time (e.g. `kedro run --parallel --runner=SequentialRunner` raises an exception).

### Applying decorators on pipelines

You can apply decorators on whole pipelines, the same way you apply decorators on single nodes. For example, if you want to apply the decorators defined in the earlier section to all pipeline nodes simultaneously, you can do so as follows:

```python
hello_pipeline = Pipeline([
    node(say_hello, 'name1', None),
    node(say_hello, 'name2', None)
]).decorate(apply_g, apply_h)

SequentialRunner().run(hello_pipeline, DataCatalog({}, dict(name1="Kedro", name2="Python")))
```

`Output`:

```console
Hello f(h(g(Kedro)))!
Hello f(h(g(Python)))!
Out[9]: {}
```

Kedro has a couple of built-in decorators, which can be useful for monitoring your pipeline. You can find the built-in decorators in `kedro.pipeline.decorators`:

 - `log_time` will log the time taken for executing your node
 - `mem_profile` will log the max memory usage of your node. `mem_profile` needs to perform at least 4 memory snapshots of your node and it will do them every 100ms, therefore it can be used only for nodes which take more than half a second to run.

## Running pipelines with IO

The above definition of pipelines only applies for non-stateful or "pure" pipelines that do not interact with the outside world. In practice, we would like to interact with APIs, databases, files and other sources of data. By combining IO and pipelines, we can tackle these more complex use cases.

By using `DataCatalog` from the IO module we are still able to write pure functions that work with our data and outsource file saving and loading to `DataCatalog`.

Through `DataCatalog`, we can control where inputs are loaded from, where intermediate variables get persisted and ultimately the location to which output variables are written:

```python
io = DataCatalog(dict(
    xs=MemoryDataSet()
))
```

```python
io.list()
```

`Output`: 

```console
Out[10]: ['xs']
```

```python
io.save('xs', [1, 2, 3])
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
io.add('v', pickler)
```

It is important to make sure that the data catalog variable name `v` matches the name `v` in the pipeline definition.

Next we can confirm that this `LambdaDataSet` works:

```python
io.save('v', 5)
```

```python
io.load('v')
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
io.load('v')
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
print(pipeline.from_inputs('m2').describe())
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
print(pipeline.from_inputs('m', 'xs').describe())
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
print(pipeline.from_nodes('mean node').describe())
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

#### Partial pipeline from nodes with tags
One can also create a partial pipeline from the nodes that have specific tags attached to them. In order to construct a partial pipeline out of nodes that have both tag `t1` *AND* tag `t2`, you can run the following:

```python
print(pipeline.only_nodes_with_tags('t1', 't2').describe())
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
partial_pipeline = pipeline.only_nodes_with_tags('t1') + pipeline.only_nodes_with_tags('t2')
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
print(pipeline.only_nodes('mean node', 'mean sos').describe())
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

#### Recreating Missing Outputs

Kedro supports the automatic generation of partial pipelines that take into account existing node outputs. This can be helpful to avoid re-running nodes which take a long time.

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
io = DataCatalog(dict(
    xs=MemoryDataSet([1, 2, 3]),
    n=n_json,
))
```

Because `n` was not saved previously, checking for its existence returns `False`:

```python
io.exists('n')
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
io.exists('n')
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
