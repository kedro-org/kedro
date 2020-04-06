# Nodes

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.
>
> In this section we introduce the concept of a node.

Relevant API documentation: [node](/kedro.pipeline.node)

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

Moreover, you can [tag all nodes in a ``Pipeline``](./06_pipelines.md#tagging-pipeline-nodes).


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


hello_node = node(say_hello, "name", None)
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
hello_node_wrapped = node(apply_g(say_hello), "name", None)

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
hello_wrapped = node(apply_g(apply_h(say_hello)), "name", None)
hello_decorated = hello_node.decorate(apply_g, apply_h)

hello_wrapped.run(dict(name="Kedro"))
hello_decorated.run(dict(name="Kedro"))
```

`Output`:

```console
Hello f(h(g(Kedro)))!
Hello f(h(g(Kedro)))!
```

Kedro comes with a few built-in decorators which are very useful when building your pipeline. You can learn more how to apply decorators to whole pipelines and the list of built-in decorators in [the next section](./06_pipelines.md#applying-decorators-on-pipelines).
