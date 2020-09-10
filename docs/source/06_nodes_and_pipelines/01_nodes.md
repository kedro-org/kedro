# Nodes

In this section we introduce the concept of a node, for which the relevant API documentation is [kedro.pipeline.node](/kedro.pipeline.node).

> *Note:* This documentation is based on `Kedro 0.16.5`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

You will first need to import libraries from Kedro and other standard tools to run the code snippets demonstrated below.

```python
from kedro.pipeline import *
from kedro.io import *
from kedro.runner import *

import pickle
import os
```

Nodes are the building blocks of pipelines and represent tasks. Pipelines are used to combine nodes to build simple machine learning workflows or even build entire end-to-end production workflows.

## Creating a pipeline node

A node is created by specifying a function, input variable names and output variable names. Let's consider a simple function that adds two numbers:

```python
def add(x, y):
    return x + y
```

The add function has two inputs `x` and `y` and a single output. A new node can now be created with this function:

```python
adder_node = node(func=add, inputs=["a", "b"], outputs="sum")
adder_node
```

`Output`:

```console
Out[1]: Node(add, ['a', 'b'], 'sum', None)
```

You can also add labels to nodes which will be used to describe them in logs:

```python
adder_node = node(func=add, inputs=["a", "b"], outputs="sum")
print(str(adder_node))

adder_node = node(func=add, inputs=["a", "b"], outputs="sum", name="adding_a_and_b")
print(str(adder_node))
```

`Output`:

```console
add([a,b]) -> [sum]
adding_a_and_b: add([a,b]) -> [sum]
```

Let's break down the node definition:

* `add` is our function that will execute when running the node
* `['a', 'b']` specify our input variable names, in this case, they are different from `x` and `y`
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
| :code:`dict(arg1='x', arg2='y')` | Keyword inputs  | :code:`def f(arg1, arg2)`   | :code:`f(arg1=x, arg2=y)`             |
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

## Tagging nodes

Tags may be useful to run partial pipelines without changing the code. For instance, `kedro run --tag=ds` will only run nodes that have a `ds` tag attached.

To tag a node, you can simply specify the `tags` argument, as follows:

```python
node(func=add, inputs=["a", "b"], outputs="sum", name="adding_a_and_b", tags="node_tag")
```

Moreover, you can [tag all nodes in a ``Pipeline``](../06_nodes_and_pipelines/02_pipelines.md#tagging-pipeline-nodes). If the pipeline definition contains the `tags=` argument, Kedro will attach the corresponding tag to every node within that pipeline.

To run a pipeline using a tag:

```bash
kedro run --tag=pipeline_tag
```

This will run only the nodes found within the pipeline tagged with `pipeline_tag`


## Running nodes

To run a node, you need to instantiate its inputs. In this case, the node expects two inputs:

```python
adder_node.run(dict(a=2, b=3))
```

`Output`:

```console
Out[2]: {'sum': 5}
```

> *Note:* It is also possible to call a node as a regular Python function: `adder_node(dict(a=2, b=3))`. This will call `adder_node.run(dict(a=2, b=3))` behind the scenes.
