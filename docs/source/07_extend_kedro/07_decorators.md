# Decorators (deprecated)

> _Note_: The decorator API will be deprecated in 0.18.0. We recommend using [Hooks](./02_hooks.md#use-hooks-to-extend-a-node-s-behaviour) to extend a node's behaviour.

A decorator is a computation that runs before and after execution. You can apply [Python decorators](https://wiki.python.org/moin/PythonDecorators) to Kedro nodes or an entire Kedro pipeline.

## How to apply a decorator to nodes

This example illustrates decorators that modify the first string argument of a given function:

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

To make sure that `apply_f` is applied to every function call, including within Kedro nodes:

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

## How to apply multiple decorators to nodes

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

## How to apply a decorator to a pipeline

Decorators can also be useful for monitoring your pipeline. You can apply one or more decorators to an entire pipeline, much as you do for a node.

For example, if you want to apply the decorator above to all pipeline nodes simultaneously:

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

## Kedro decorators

Kedro currently has one built-in decorator: `log_time`, which logs the time taken to execute a node. You can find it in [`kedro.pipeline.decorators`](/kedro.pipeline.decorators.log_time).

Other decorators can be found in [`kedro.extras.decorators`](/kedro.extras.decorators), for which you will need to install the required dependencies.
