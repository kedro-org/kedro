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

[Generator functions](https://learnpython.org/en/Generators) were introduced with [PEP 255](https://www.python.org/dev/peps/pep-0255). They are a special kind of function that returns lazy iterators, which are often used for lazy-loading or lazy-saving. It does not store their entire contents in memory all at once so it can be useful to process large dataset that does not fit in memory.

The following code uses a `pandas chunksize` generator to process large datasets within the [`pandas-iris` starter](../kedro_project_setup/starters.md).


### Set up the pandas-iris project
  First set up a project by following the [get started guide](../get_started/new_project.md#create-a-new-project-containing-example-code) to create a Kedro project with the `pandas-iris` starter example code.


To use generators, we will do three things:
- change `return` to `yield`
- Create a [custom dataset](../extend_kedro/custom_datasets.md) called `ChunkWiseCSVDataSet`
- Update `catalog.yml` to use the `ChunkWiseCSVDataSet`



### Use Generators as Inputs
Thanks to `pandas` built-in support, you can use the `chunksize` argument to read data using generator.

You need to update your `catalog.yml` as follow:
```yaml
example_iris_data:
  type: pandas.CSVDataSet
  filepath: data/01_raw/iris.csv
  load_args:
    chunksize: 1000

X_train_chunk:
  type: chunk_process.extras.datasets.chunkwise.ChunkWiseCSVDataSet
  filepath: data/02_intermediate/iris.csv
  load_args:
    chunksize: 1000
  save_args:
    mode: "a+" # append
```

### Use Generators as Outputs
To save data lazily, you will need to create a custom dataset.


 This `ChunkWise` is a variant of the `pandas.CSVDataSet` where the main change is to the `_save` method which should save the data in append-or-create mode, `ab+` (append, binary or create mode).

<details>
<summary><b>Click to expand</b></summary>

```python
from copy import deepcopy
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any, Dict

import fsspec
import pandas as pd

from kedro.io.core import (
    AbstractVersionedDataSet,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)
from kedro.extras.datasets.pandas import CSVDataSet

class ChunkWiseCSVDataSet(CSVDataSet):
    """``ChunkWiseCSVDataSet`` loads/saves data from/to a CSV file using an underlying
    filesystem. It uses pandas to handle the CSV file.
    """

    def _save(self, data: pd.DataFrame) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)
        buf = BytesIO()
        data.to_csv(path_or_buf=buf, **self._save_args)

        with self._fs.open(save_path, mode="ab+") as fs_file:
            fs_file.write(buf.getvalue())
```
</details>

After that, you need to make two changes:
- Update the definition of `split_data` so it use `yield` instead of `return`

Run `kedro run` in your terminal, you should be able to see logs similar to this


You will see the repeat logs indicating the data is saved as multiple chunks.

```
...
                    INFO     Saving data to 'X_train_chunk' (ChunkWiseCSVDataSet)...      data_catalog.py:514
                    INFO     Saving data to 'X_train_chunk' (ChunkWiseCSVDataSet)...      data_catalog.py:514
...
```