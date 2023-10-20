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

[Generator functions](https://learnpython.org/en/Generators) were introduced with [PEP 255](https://www.python.org/dev/peps/pep-0255) and are a special kind of function in Python that returns lazy iterators. They are often used for lazy-loading or lazy-saving of data, which can be particularly useful when dealing with large datasets that do not fit entirely into memory. In the context of Kedro, generator functions can be used in nodes to efficiently process and handle such large datasets.


### Set up the project

To demonstrate the use of generator functions in Kedro nodes, first, set up a Kedro project using the `pandas-iris` starter. If you haven't already created a Kedro project, you can follow the [get started guide](../get_started/new_project.md#create-a-new-project-containing-example-code) to create it.

Create the project with this command:
```bash
kedro new -s pandas-iris
```

### Loading data with Generators
To use generator functions in Kedro nodes, you need to update the `catalog.yml` file to include the `chunksize` argument for the relevant dataset that will be processed using the generator.

You need to add a new dataset in your `catalog.yml` as follows:
```diff
+ X_test:
+  type: pandas.CSVDataset
+  filepath: data/05_model_input/X_test.csv
+  load_args:
+    chunksize: 10
```

With `pandas` built-in support, you can use the `chunksize` argument to read data using generator.

### Saving data with Generators
To use generators to save data lazily, you need do three things:
- Update the `make_prediction` function definition to use `yield` instead of `return`.
- Create a [custom dataset](../data/how_to_create_a_custom_dataset.md) called `ChunkWiseCSVDataset`
- Update `catalog.yml` to use a newly created `ChunkWiseCSVDataset`.

Copy the following code to `nodes.py`. The main change is to use a new model `DecisionTreeClassifier` to make prediction by chunks in `make_predictions`.

<details>
<summary><b>Click to open</b></summary>

```python
import logging
from typing import Any, Dict, Tuple, Iterator
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
import numpy as np
import pandas as pd


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

    data_train = data.sample(
        frac=parameters["train_fraction"], random_state=parameters["random_state"]
    )
    data_test = data.drop(data_train.index)

    X_train = data_train.drop(columns=parameters["target_column"])
    X_test = data_test.drop(columns=parameters["target_column"])
    y_train = data_train[parameters["target_column"]]
    y_test = data_test[parameters["target_column"]]

    label_encoder = LabelEncoder()
    label_encoder.fit(pd.concat([y_train, y_test]))
    y_train = label_encoder.transform(y_train)

    return X_train, X_test, y_train, y_test


def make_predictions(
    X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.Series
) -> pd.Series:
    """Use a DecisionTreeClassifier model to make prediction."""
    model = DecisionTreeClassifier()
    model.fit(X_train, y_train)

    for chunk in X_test:
        y_pred = model.predict(chunk)
        y_pred = pd.DataFrame(y_pred)
        yield y_pred


def report_accuracy(y_pred: pd.Series, y_test: pd.Series):
    """Calculates and logs the accuracy.

    Args:
        y_pred: Predicted target.
        y_test: True target.
    """
    accuracy = accuracy_score(y_test, y_pred)
    logger = logging.getLogger(__name__)
    logger.info("Model has accuracy of %.3f on test data.", accuracy)
```
</details>


The `ChunkWiseCSVDataset` is a variant of the `pandas.CSVDataset` where the main change is to the `_save` method that appends data instead of overwriting it. You need to create a file `src/<package_name>/chunkwise.py` and put this class inside it. Below is an example of the `ChunkWiseCSVDataset` implementation:

```python
import pandas as pd

from kedro.io.core import (
    get_filepath_str,
)
from kedro_datasets.pandas import CSVDataset


class ChunkWiseCSVDataset(CSVDataset):
    """``ChunkWiseCSVDataset`` loads/saves data from/to a CSV file using an underlying
    filesystem. It uses pandas to handle the CSV file.
    """

    _overwrite = True

    def _save(self, data: pd.DataFrame) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)
        # Save the header for the first batch
        if self._overwrite:
            data.to_csv(save_path, index=False, mode="w")
            self._overwrite = False
        else:
            data.to_csv(save_path, index=False, header=False, mode="a")
```

After that, you need to update the `catalog.yml` to use this new dataset.

```diff
+ y_pred:
+  type: <package_name>.chunkwise.ChunkWiseCSVDataset
+  filepath: data/07_model_output/y_pred.csv
```

With these changes, when you run `kedro run` in your terminal, you should see `y_pred` being saved multiple times in the logs as the generator lazily processes and saves the data in smaller chunks.

```
...
                    INFO     Loading data from 'y_train' (MemoryDataset)...                                                                                         data_catalog.py:475
                    INFO     Running node: make_predictions: make_predictions([X_train,X_test,y_train]) -> [y_pred]                                                         node.py:331
                    INFO     Saving data to 'y_pred' (ChunkWiseCSVDataset)...                                                                                       data_catalog.py:514
                    INFO     Saving data to 'y_pred' (ChunkWiseCSVDataset)...                                                                                       data_catalog.py:514
                    INFO     Saving data to 'y_pred' (ChunkWiseCSVDataset)...                                                                                       data_catalog.py:514
                    INFO     Completed 2 out of 3 tasks                                                                                                         sequential_runner.py:85
                    INFO     Loading data from 'y_pred' (ChunkWiseCSVDataset)...                                                                                    data_catalog.py:475
...                                                                              runner.py:105
```
