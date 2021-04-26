# Pipelines

> *Note:* This documentation is based on `Kedro 0.17.1`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

We previously introduced [Nodes](./01_nodes.md) as building blocks that represent tasks, and which can be combined in a pipeline to build your workflow.  A pipeline organises the dependencies and execution order of your collection of nodes, and connects inputs and outputs while keeping your code modular. The pipeline determines the node execution order by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

To benefit from Kedro's automatic dependency resolution, you can chain your nodes into a [pipeline](/kedro.pipeline.Pipeline), which is a list of nodes that use a shared set of variables.

## How to build a pipeline

In the following example, we construct a simple pipeline that computes the variance of a set of numbers. In practice, pipelines can use more complicated node definitions and the variables they use usually correspond to entire datasets:

<details>
<summary><b>Click to expand</b></summary>


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
        node(mean, ["xs", "n"], "m", name="mean_node"),
        node(mean_sos, ["xs", "n"], "m2", name="mean_sos"),
        node(variance, ["m", "m2"], "v", name="variance_node"),
    ]
)
```
</details>

You can use `describe` to understand what nodes are part of the pipeline:

<details>
<summary><b>Click to expand</b></summary>

```python
print(pipeline.describe())
```

The output is as follows:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean_node
mean_sos
variance_node

Outputs: v
##################################
```
</details>

### How to tag a pipeline

You can also tag your pipeline by providing the `tags` argument, which will tag all of the pipeline's nodes. In the following example, both nodes are tagged with `pipeline_tag`.

```python
pipeline = Pipeline(
    [node(..., name="node1"), node(..., name="node2")], tags="pipeline_tag",
)
```

You can combine pipeline tagging with node tagging. In the following example, `node1` and `node2` are tagged with `pipeline_tag`, while `node2` also has a `node_tag`.

```python
pipeline = Pipeline(
    [node(..., name="node1"), node(..., name="node2", tags="node_tag")],
    tags="pipeline_tag",
)
```


### How to merge multiple pipelines

You can merge multiple pipelines as shown below. Note that, in this case, `pipeline_de` and `pipeline_ds` are expanded to a list of their underlying nodes and these are merged together:

<details>
<summary><b>Click to expand</b></summary>


```python
pipeline_de = Pipeline([node(len, "xs", "n"), node(mean, ["xs", "n"], "m")])

pipeline_ds = Pipeline(
    [node(mean_sos, ["xs", "n"], "m2"), node(variance, ["m", "m2"], "v")]
)

last_node = node(print, "v", None)

pipeline_all = Pipeline([pipeline_de, pipeline_ds, last_node])
print(pipeline_all.describe())
```

The output is as follows:

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
</details>


### Information about the nodes in a pipeline

Pipelines provide access to their nodes in a topological order to enable custom functionality, e.g. pipeline visualisation. Each node has information about its inputs and outputs:

<details>
<summary><b>Click to expand</b></summary>

```python
nodes = pipeline.nodes
nodes
```

The output is as follows:

```python
[
    Node(len, "xs", "n", None),
    Node(mean, ["xs", "n"], "m", "mean_node"),
    Node(mean_sos, ["xs", "n"], "m2", "mean_sos"),
    Node(variance, ["m", "m2"], "v", "variance node"),
]
```

To find out about the inputs:

```python
nodes[0].inputs
```

You should see the following:

```python
["xs"]
```
</details>

### Information about pipeline inputs and outputs
In a similar way to the above, you can use `inputs()` and `outputs()` to check the inputs and outputs of a pipeline:

```python
pipeline.inputs()
```

Gives the following:

```console
Out[7]: {'xs'}
```

```python
pipeline.outputs()
```

Displays the output:

```console
Out[8]: {'v'}
```


## Bad pipelines

A pipelines can usually readily resolve its dependencies. In some cases, resolution is not possible. In this case, the pipeline is not well-formed.

### Pipeline with bad nodes

In this case we have a pipeline consisting of a single node with no input and output:

<details>
<summary><b>Click to expand</b></summary>

```python
try:
    Pipeline([node(lambda: print("!"), None, None)])
except Exception as e:
    print(e)
```

Gives the following output:

```console
Invalid Node definition: it must have some `inputs` or `outputs`.
Format should be: node(function, inputs, outputs)
```

</details>

### Pipeline with circular dependencies

For every two variables where the first depends on the second, there must not be a way in which the second also depends on the first, otherwise, a circular dependency will prevent us from compiling the pipeline.

The first node captures the relationship of how to calculate `y` from `x` and the second captures the relationship of how to calculate `x` knowing `y`. The pair of nodes cannot co-exist in the same pipeline:

<details>
<summary><b>Click to expand</b></summary>

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

The output is as follows:

```console
Circular dependencies exist among these items: ['first node: <lambda>([x]) -> [y]', 'second node: <lambda>([y]) -> [x]']
```
</details>
