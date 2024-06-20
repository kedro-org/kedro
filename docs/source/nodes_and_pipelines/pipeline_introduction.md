# Pipeline objects

We previously introduced [Nodes](./nodes.md) as building blocks that represent tasks, and can be combined in a pipeline to build your workflow. A pipeline organises the dependencies and execution order of your collection of nodes, and connects inputs and outputs while keeping your code modular. The pipeline resolves dependencies to determine the node execution order, and does *not* necessarily run the nodes in the order in which they are passed in.

To benefit from Kedro's automatic dependency resolution, you can chain your nodes into a {py:class}`~kedro.pipeline.Pipeline`, which is a list of nodes that use a shared set of variables. That class could be created using {py:class}`~kedro.pipeline.modular_pipeline.pipeline` method, based on nodes or other pipelines (in which case all nodes from that pipeline will be used).

- [How to build a pipeline](#how-to-build-a-pipeline)
- [How to use `describe` to discover what nodes are part of the pipeline](#how-to-use-describe-to-discover-what-nodes-are-part-of-the-pipeline)
- [How to merge multiple pipelines](#how-to-merge-multiple-pipelines)
- [How to receive information about the nodes in a pipeline](#how-to-receive-information-about-the-nodes-in-a-pipeline)
- [How to receive information about pipeline inputs and outputs](#how-to-receive-information-about-pipeline-inputs-and-outputs)
- [How to tag a pipeline](#how-to-tag-a-pipeline)
- [How to avoid creating bad pipelines](#how-to-avoid-creating-bad-pipelines)
- [How to store pipeline code in a kedro project](#how-to-store-pipeline-code-in-a-kedro-project)






## How to build a pipeline

In the following example, we construct a simple pipeline that computes the variance of a set of numbers. In practice, pipelines can use more complicated node definitions, and the variables they use usually correspond to entire datasets:

```python
from kedro.pipeline import pipeline, node

def mean(xs, n):
    return sum(xs) / n

def mean_sos(xs, n):
    return sum(x**2 for x in xs) / n

def variance(m, m2):
    return m2 - m * m


variance_pipeline = pipeline(
    [
        node(len, "xs", "n"),
        node(mean, ["xs", "n"], "m", name="mean_node"),
        node(mean_sos, ["xs", "n"], "m2", name="mean_sos"),
        node(variance, ["m", "m2"], "v", name="variance_node"),
    ]
)
```

Kedro determines the order of execution of these nodes based on the inputs and outputs specified for each node. In this example:
1. The first node computes the length of `xs` and outputs it as `n`.
2. The second node calculates the mean using `xs` and `n`, and outputs it as `m`.
3. The third node computes the mean sum of squares (mean_sos) using `xs` and `n`, and outputs it as `m2`.
4. The fourth node calculates the variance using the mean (`m`) and mean sum of squares (`m2`), and outputs it as `v`.

Kedro's dependency resolution ensures that each node runs only after its required inputs are available from the outputs of previous nodes. This way, the nodes are executed in the correct order automatically, based on the defined dependencies.


## How to use `describe` to discover what nodes are part of the pipeline

```python
print(variance_pipeline.describe())
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

## How to merge multiple pipelines

You can merge multiple pipelines as shown below. Note that, in this case, `pipeline_de` and `pipeline_ds` are expanded to a list of their underlying nodes and these are merged together:

```python
pipeline_de = pipeline([node(len, "xs", "n"), node(mean, ["xs", "n"], "m")])

pipeline_ds = pipeline(
    [node(mean_sos, ["xs", "n"], "m2"), node(variance, ["m", "m2"], "v")]
)

last_node = node(print, "v", None)

pipeline_all = pipeline([pipeline_de, pipeline_ds, last_node])
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


## How to receive information about the nodes in a pipeline

Pipelines provide access to their nodes in a topological order to enable custom functionality, e.g. pipeline visualisation. Each node has information about its inputs and outputs:

```python
nodes = variance_pipeline.nodes
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

## How to receive information about pipeline inputs and outputs

In a similar way to the above, you can use `inputs()` and `outputs()` to check the inputs and outputs of a pipeline:

```python
variance_pipeline.inputs()
```

Gives the following:

```console
Out[7]: {'xs'}
```

```python
variance_pipeline.outputs()
```

Displays the output:

```console
Out[8]: {'v'}
```


## How to tag a pipeline

You can also tag your pipeline by providing the `tags` argument, which will tag all of the pipeline's nodes. In the following example, both nodes are tagged with `pipeline_tag`.

```python
pipeline = pipeline(
    [node(..., name="node1"), node(..., name="node2")], tags="pipeline_tag"
)
```

You can combine pipeline tagging with node tagging. In the following example, `node1` and `node2` are tagged with `pipeline_tag`, while `node2` also has a `node_tag`.

```python
pipeline = pipeline(
    [node(..., name="node1"), node(..., name="node2", tags="node_tag")],
    tags="pipeline_tag",
)
```

## How to avoid creating bad pipelines

A pipelines can usually readily resolve its dependencies. In some cases, resolution is not possible. In this case, the pipeline is not well-formed.

### Pipeline with bad nodes

In this case, we have a pipeline consisting of a single node with no input and output:


```python
try:
    pipeline([node(lambda: print("!"), None, None)])
except Exception as e:
    print(e)
```

Gives the following output:

```console
Invalid Node definition: it must have some `inputs` or `outputs`.
Format should be: node(function, inputs, outputs)
```


### Pipeline with circular dependencies

For every two variables where the first depends on the second, there must not be a way in which the second also depends on the first, otherwise, a circular dependency will prevent us from compiling the pipeline.

The first node captures the relationship of how to calculate `y` from `x` and the second captures the relationship of how to calculate `x` knowing `y`. The pair of nodes cannot co-exist in the same pipeline:


```python
try:
    pipeline(
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

### Pipeline nodes named with the dot notation
Nodes named with dot notation may behave strangely.

```python
pipeline([node(lambda x: x, inputs="input1kedro", outputs="output1.kedro")])
```

Nodes that are created with input or output names that contain `.` risk a disconnected pipeline or improperly-formatted Kedro structure.

This is because `.` has a special meaning internally and indicates a namespace pipeline. In the example, the outputs segment should be disconnected as the name implies there is an "output1" namespace pipeline. The input is not namespaced, but the output is via its dot notation. This leads to Kedro processing each separately. For this example, a better approach would've been writing both as `input1_kedro` and `output1_kedro`.

We recommend use of characters like `_` instead of `.` as name separators.


## How to store pipeline code in a kedro project

When managing your Kedro project, we recommend grouping related tasks into individual pipelines to achieve modularity. A project typically contains many tasks, and organising frequently executed tasks together into separate pipelines helps maintain order and efficiency. Each pipeline should ideally be organised in its own folder, promoting easy copying and reuse within and between projects. Simply put: one pipeline, one folder. To assist with this, Kedro introduces the concept of [Modular Pipelines](modular_pipelines.md), which are described in the next section.
