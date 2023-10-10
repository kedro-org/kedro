# Slice a pipeline

Sometimes it is desirable to run a subset, or a 'slice' of a pipeline's nodes. In this page, we illustrate the programmatic options that Kedro provides. You can also use the [Kedro CLI to pass parameters to `kedro run`](../development/commands_reference.md#run-the-project) command and slice a pipeline.

Let's look again at the example pipeline from the [pipeline introduction documentation](./pipeline_introduction.md#how-to-build-a-pipeline), which computes the variance of a set of numbers:

<details>
<summary><b>Click to expand</b></summary>


```python
def mean(xs, n):
    return sum(xs) / n


def mean_sos(xs, n):
    return sum(x**2 for x in xs) / n


def variance(m, m2):
    return m2 - m * m


full_pipeline = pipeline(
    [
        node(len, "xs", "n"),
        node(mean, ["xs", "n"], "m", name="mean_node", tags="mean"),
        node(mean_sos, ["xs", "n"], "m2", name="mean_sos", tags=["mean", "variance"]),
        node(variance, ["m", "m2"], "v", name="variance_node", tags="variance"),
    ]
)
```
</details>

The `Pipeline.describe()` method returns the following output:

<details>
<summary><b>Click to expand</b></summary>


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



## Slice a pipeline by providing inputs
One way to slice a pipeline is to provide a set of pre-calculated inputs which should serve as a start of the pipeline. For example, in order to slice the pipeline to run from input `m2` downstream you can specify it like this:

<details>
<summary><b>Click to expand</b></summary>


```python
print(full_pipeline.from_inputs("m2").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: m, m2

variance_node

Outputs: v
##################################
```
</details>

Slicing the pipeline from inputs `m` and `xs` results in the following pipeline:

<details>
<summary><b>Click to expand</b></summary>

```python
print(full_pipeline.from_inputs("m", "xs").describe())
```

`Output`:

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

As you can see, adding `m` in the `from_inputs` list does not guarantee that it will not be recomputed if another input like `xs` is specified.

## Slice a pipeline by specifying nodes
Another way of slicing a pipeline is to specify the nodes which should be used as a start of the new pipeline. For example:

<details>
<summary><b>Click to expand</b></summary>

```python
print(full_pipeline.from_nodes("mean_node").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: m2, n, xs

mean_node
variance_node

Outputs: v
##################################
```
</details>

As you can see, this will slice the pipeline and run it from the specified node to all other nodes downstream.

You can run the resulting pipeline slice by running the following command in your terminal window:

```bash
kedro run --from-nodes=mean_node
```

## Slice a pipeline by specifying final nodes
Similarly, you can specify the nodes which should be used to end a pipeline. For example:

<details>
<summary><b>Click to expand</b></summary>


```python
print(full_pipeline.to_nodes("mean_node").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean_node

Outputs: m
##################################
```
</details>

As you can see, this will slice the pipeline, so it runs from the beginning and ends with the specified node:

```bash
kedro run --to-nodes=mean_node
```

You can also slice a pipeline by specifying the start and finish nodes, and thus the set of nodes to be included in the pipeline slice:

```bash
kedro run --from-nodes=A --to-nodes=Z
```

or, when specifying multiple nodes:

```bash
kedro run --from-nodes=A,D --to-nodes=X,Y,Z
```

## Slice a pipeline with tagged nodes
You can also slice a pipeline from the nodes that have specific tags attached to them. For example, for nodes that have both tag `mean` *AND* tag `variance`, you can run the following:

<details>
<summary><b>Click to expand</b></summary>

```python
print(full_pipeline.only_nodes_with_tags("mean", "variance").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Inputs: n, xs

mean_sos

Outputs: m2
##################################
```
</details>


To slice a pipeline from nodes that have tag `mean` *OR* tag `variance`:

<details>
<summary><b>Click to expand</b></summary>


```python
sliced_pipeline = full_pipeline.only_nodes_with_tags(
    "mean"
) + full_pipeline.only_nodes_with_tags("variance")
print(sliced_pipeline.describe())
```

`Output`:

```console
#### Pipeline execution order ####
Inputs: n, xs

mean
mean_sos
variance

Outputs: v
##################################
```
</details>

## Slice a pipeline by running specified nodes
Sometimes you might need to run only some of the nodes in a pipeline, as follows:

<details>
<summary><b>Click to expand</b></summary>

```python
print(full_pipeline.only_nodes("mean_node", "mean_sos").describe())
```

`Output`:

```console
#### Pipeline execution order ####
Name: None
Inputs: n, xs

mean_node
mean_sos

Outputs: m, m2
##################################
```
</details>

This will create a sliced pipeline, comprised of the nodes you specify in the method call.

```{note}
All the inputs required by the specified nodes must exist, i.e. already produced or present in the data catalog.
```

## How to recreate missing outputs

Kedro can automatically generate a sliced pipeline from existing node outputs. This can be helpful if you want to avoid re-running nodes that take a long time:

<details>
<summary><b>Click to expand</b></summary>

```python
print(full_pipeline.describe())
```

`Output`:

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

To demonstrate this, let us save the intermediate output `n` using a `JSONDataset`.

<details>
<summary><b>Click to expand</b></summary>

```python
from kedro_datasets.pandas import JSONDataset
from kedro.io import DataCatalog, MemoryDataset

n_json = JSONDataset(filepath="./data/07_model_output/len.json")
io = DataCatalog(dict(xs=MemoryDataset([1, 2, 3]), n=n_json))
```
</details>

Because `n` was not saved previously, checking for its existence returns `False`:

<details>
<summary><b>Click to expand</b></summary>


```python
io.exists("n")
```

`Output`:

```console
Out[15]: False
```
</details>

Running the pipeline calculates `n` and saves the result to disk:

<details>
<summary><b>Click to expand</b></summary>

```python
SequentialRunner().run(full_pipeline, io)
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
</details>

We can avoid re-calculating `n` (and all other results that have already been saved) by using the `Runner.run_only_missing` method. Note that the first node of the original pipeline (`len([xs]) -> [n]`) has not been run:

<details>
<summary><b>Click to expand</b></summary>

```python
SequentialRunner().run_only_missing(full_pipeline, io)
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
</details>
