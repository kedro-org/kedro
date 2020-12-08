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
kedro run --from-nodes="mean_node"
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


#### Recreating missing outputs

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

To demonstrate this, let us save the intermediate output `n` using a `JSONDataSet`.

```python
from kedro.extras.datasets.pandas import JSONDataSet
from kedro.io import DataCatalog, MemoryDataSet

n_json = JSONDataSet(filepath="./data/07_model_output/len.json")
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
