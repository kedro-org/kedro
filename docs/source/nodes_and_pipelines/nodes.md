# Nodes

In this section, we introduce the concept of a node, for which the relevant API documentation is [kedro.pipeline.node](/kedro.pipeline.node).

Nodes are the building blocks of pipelines, and represent tasks. Pipelines are used to combine nodes to build workflows, which range from simple machine learning workflows to end-to-end (E2E) production workflows.

You must first import libraries from Kedro and other standard tools to run the code snippets demonstrated below.

```python
from kedro.pipeline import *
from kedro.io import *
from kedro.runner import *

import pickle
import os
```

## How to create a node

A node is created by specifying a function, input variable names and output variable names. Let's consider a simple function that adds two numbers:

```python
def add(x, y):
    return x + y
```

The function has two inputs (`x` and `y`) and a single output (the sum of the inputs).

Here is how a node is created with this function:

```python
adder_node = node(func=add, inputs=["a", "b"], outputs="sum")
adder_node
```

Here is the output:

```console
Out[1]: Node(add, ['a', 'b'], 'sum', None)
```

You can also add labels to nodes, which will be used to describe them in logs:

```python
adder_node = node(func=add, inputs=["a", "b"], outputs="sum")
print(str(adder_node))

adder_node = node(func=add, inputs=["a", "b"], outputs="sum", name="adding_a_and_b")
print(str(adder_node))
```

This gives the following output:

```console
add([a,b]) -> [sum]
adding_a_and_b: add([a,b]) -> [sum]
```

Let's break down the node definition:

* `add` is the Python function that will execute when the node runs
* `['a', 'b']` specify the input variable names
* `sum` specifies the return variable name. The value returned by `add` will be bound in this variable
* `name` is an optional label for the node, which can be used to provide description of the business logic it provides

### Node definition syntax

A syntax describes function inputs and outputs. This syntax allows different Python functions to be reused in nodes, and supports dependency resolution in pipelines.

### Syntax for input variables

| Input syntax               | Meaning         | Example function parameters | How function is called when node runs |
| -------------------------- | --------------- | --------------------------- | ------------------------------------- |
| `None`                     | No input        | `def f()`                   | `f()`                                 |
| `'a'`                      | Single input    | `def f(arg1)`               | `f(a)`                                |
| `['a', 'b']`               | Multiple inputs | `def f(arg1, arg2)`         | `f(a, b)`                             |
| `dict(arg1='x', arg2='y')` | Keyword inputs  | `def f(arg1, arg2)`         | `f(arg1=x, arg2=y)`                   |

### Syntax for output variables

| Output syntax              | Meaning           | Example return statement            |
| -------------------------- | ----------------- | ----------------------------------- |
| `None`                     | No output         | Does not return                     |
| `'a'`                      | Single output     | `return a`                          |
| `['a', 'b']`               | List output       | `return [a, b]`                     |
| `dict(key1='a', key2='b')` | Dictionary output | `return dict(key1=a, key2=b)`       |

Any combinations of the above are possible, except nodes of the form `node(f, None, None)` (at least a single input or output must be provided).

## `**kwargs`-only node functions

Sometimes, when creating reporting nodes for instance, you need to know the names of the datasets that your node receives, but you might not have this information in advance. This can be solved by defining a `**kwargs`-only function:

```python
def reporting(**kwargs):
    result = []
    for name, data in kwargs.items():
        res = example_report(name, data)
        result.append(res)
    return combined_report(result)
```

Then, when it comes to constructing the `Node`, simply pass a dictionary to the node inputs:

```python
from kedro.pipeline import node


uk_reporting_node = node(
    reporting,
    inputs={"uk_input1": "uk_input1", "uk_input2": "uk_input2", ...},
    outputs="uk",
)

ge_reporting_node = node(
    reporting,
    inputs={"ge_input1": "ge_input1", "ge_input2": "ge_input2", ...},
    outputs="ge",
)
```

Alternatively, you can also make use of a helper function that creates the mapping for you, so you can reuse it across your codebase.

```diff
 from kedro.pipeline import node


+mapping = lambda x: {k: k for k in x}
+
 uk_reporting_node = node(
     reporting,
-    inputs={"uk_input1": "uk_input1", "uk_input2": "uk_input2", ...},
+    inputs=mapping(["uk_input1", "uk_input2", ...]),
     outputs="uk",
 )

 ge_reporting_node = node(
     reporting,
-    inputs={"ge_input1": "ge_input1", "ge_input2": "ge_input2", ...},
+    inputs=mapping(["ge_input1", "ge_input2", ...]),
     outputs="ge",
 )
```


## How to tag a node

Tags might be useful to run part of a pipeline without changing the code. For instance, `kedro run --tag=ds` will only run nodes that have a `ds` tag attached.

To tag a node, you can simply specify the `tags` argument:

```python
node(func=add, inputs=["a", "b"], outputs="sum", name="adding_a_and_b", tags="node_tag")
```

Moreover, you can [tag all nodes in a `Pipeline`](./pipeline_introduction.md#how-to-tag-a-pipeline). If the pipeline definition contains the `tags=` argument, Kedro will attach the corresponding tag to every node within that pipeline.

To run a pipeline using a tag:

```bash
kedro run --tag=pipeline_tag
```

This will run only the nodes found within the pipeline tagged with `pipeline_tag`.


## How to run a node

To run a node, you must instantiate its inputs. In this case, the node expects two inputs:

```python
adder_node.run(dict(a=2, b=3))
```

The output is as follows:

```console
Out[2]: {'sum': 5}
```

```{note}
You can also call a node as a regular Python function: `adder_node(dict(a=2, b=3))`. This will call `adder_node.run(dict(a=2, b=3))` behind the scenes.
```

## How to use generator functions in a node

Generator functions are useful for providing lazy iterators to search for items without storing in memory. We can wrap generator functions in a Kedro pipeline and save the result by calling the dataset's `save` method separately for each chunk.
The following example will show you how to utilise `pandas chunksize` generator to process large datasets:

We need to create a [custom dataset](https://kedro.readthedocs.io/en/stable/extend_kedro/custom_datasets.html) with `_load` having `chunksize` parameter for `pd.read_csv()` and `_save` should save the data in append-or-create mode, `a+`.

```python
def _load(self) -> pd.DataFrame:
    load_path = str(self._get_load_path())
    return pd.read_csv(load_path, **self._load_args, chunksize=50)

def _save(self, data: pd.DataFrame) -> None:
    save_path = get_filepath_str(self._get_save_path(), self._protocol)

    buf = BytesIO()
    data.to_csv(path_or_buf=buf, **self._save_args)

    with self._fs.open(save_path, mode="a+") as fs_file:
        fs_file.write(buf.getvalue())
```

Using the `pandas-iris` starter as an example we will repurpose `split_dataset` function to process chunk-wise data:

```python
def split_data(
    data: pd.DataFrame, parameters: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Splits data into features and target training and test sets.

    Args:
        data: Data containing features and target.
        parameters: Parameters defined in parameters.yml.
    Returns:
        Split data.
    """
    for chunk in data:
        full_data = pd.concat([chunk])
        data_train = full_data.sample(
            frac=parameters["train_fraction"], random_state=parameters["random_state"]
        )
        data_test = full_data.drop(data_train.index)

        X_train = data_train.drop(columns=parameters["target_column"])
        X_test = data_test.drop(columns=parameters["target_column"])
        y_train = data_train[parameters["target_column"]]
        y_test = data_test[parameters["target_column"]]
        yield X_train, X_test, y_train, y_test
```

When we now do `kedro run` the output should now be saving `X_train`, `X_test`, `y_train`, `y_test`in chunks:

```
...
[02/09/23 13:21:57] INFO     Loading data from 'example_iris_data' (CustomDataSet)...                                                                                data_catalog.py:343
                    INFO     Loading data from 'parameters' (MemoryDataSet)...                                                                                     data_catalog.py:343
                    INFO     Running node: split: split_data([example_iris_data,parameters]) -> [X_train,X_test,y_train,y_test]                                            node.py:329
                    INFO     Saving data to 'X_train' (MemoryDataSet)...                                                                                           data_catalog.py:382
                    INFO     Saving data to 'X_test' (MemoryDataSet)...                                                                                            data_catalog.py:382
                    INFO     Saving data to 'y_train' (MemoryDataSet)...                                                                                           data_catalog.py:382
                    INFO     Saving data to 'y_test' (MemoryDataSet)...                                                                                            data_catalog.py:382
                    INFO     Saving data to 'X_train' (MemoryDataSet)...                                                                                           data_catalog.py:382
                    INFO     Saving data to 'X_test' (MemoryDataSet)...                                                                                            data_catalog.py:382
                    INFO     Saving data to 'y_train' (MemoryDataSet)...                                                                                           data_catalog.py:382
                    INFO     Saving data to 'y_test' (MemoryDataSet)...                                                                                            data_catalog.py:382
                    INFO     Completed 1 out of 3 tasks                                                                                                        sequential_runner.py:85
...
```