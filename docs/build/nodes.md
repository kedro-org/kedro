# Nodes

In this section, we introduce the concept of a node, for which the relevant API documentation is [`node`][kedro.pipeline.node].

Nodes are the building blocks of pipelines, and represent tasks. Pipelines are used to combine nodes to build workflows, which range from basic machine learning workflows to end-to-end (E2E) production workflows.

You must first import libraries from Kedro and other standard tools to run the code snippets below.

```python
from kedro.pipeline import *
from kedro.io import *
from kedro.runner import *

import pickle
import os
```

## How to create a node

A node is created by specifying a function, input variable names and output variable names. Let's consider a function that adds two numbers:

```python
def add(x, y):
    return x + y
```

The function has two inputs (`x` and `y`) and a single output (the sum of the inputs).

Here is how a node is created with this function:

```python
adder_node = Node(func=add, inputs=["a", "b"], outputs="sum")
adder_node
```

Here is the output:

```console
Out[1]: Node(add, ['a', 'b'], 'sum', None)
```

You can also add labels to nodes, which will be used to describe them in logs:

```python
adder_node = Node(func=add, inputs=["a", "b"], outputs="sum")
print(str(adder_node))

adder_node = Node(func=add, inputs=["a", "b"], outputs="sum", name="adding_a_and_b")
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
| `['a', 'b', 'c']`          | Variable inputs | `def f(arg1, *args)`.       | `f(arg1, arg2, arg3)`                 |
| `dict(arg1='x', arg2='y')` | Keyword inputs  | `def f(arg1, arg2)`         | `f(arg1=x, arg2=y)`                   |

### Syntax for output variables

| Output syntax              | Meaning           | Example return statement            |
| -------------------------- | ----------------- | ----------------------------------- |
| `None`                     | No output         | Does not return                     |
| `'a'`                      | Single output     | `return a`                          |
| `['a', 'b']`               | List output       | `return [a, b]`                     |
| `dict(key1='a', key2='b')` | Dictionary output | `return dict(key1=a, key2=b)`       |

Any combinations of the above are possible, except nodes of the form `Node(f, None, None)` (at least a single input or output must be provided).

## `*args` node functions
It is common to have functions that take an arbitrary number of inputs, like a function that combines multiple dataframes. You can use the `*args` argument in the node function, while declaring the names of the datasets in the node's inputs.

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

Then, when it comes to constructing the `Node`, pass a dictionary to the node inputs:

```python
from kedro.pipeline import Node


uk_reporting_node = Node(
    reporting,
    inputs={"uk_input1": "uk_input1", "uk_input2": "uk_input2", ...},
    outputs="uk",
)

ge_reporting_node = Node(
    reporting,
    inputs={"ge_input1": "ge_input1", "ge_input2": "ge_input2", ...},
    outputs="ge",
)
```

You can also make use of a helper function that creates the mapping for you, so you can reuse it across your codebase.

```diff
 from kedro.pipeline import Node


+mapping = lambda x: {k: k for k in x}
+
 uk_reporting_node = Node(
     reporting,
-    inputs={"uk_input1": "uk_input1", "uk_input2": "uk_input2", ...},
+    inputs=mapping(["uk_input1", "uk_input2", ...]),
     outputs="uk",
 )

 ge_reporting_node = Node(
     reporting,
-    inputs={"ge_input1": "ge_input1", "ge_input2": "ge_input2", ...},
+    inputs=mapping(["ge_input1", "ge_input2", ...]),
     outputs="ge",
 )
```


## How to tag a node

Tags might be useful to run part of a pipeline without changing the code. For instance, `kedro run --tags=ds` runs nodes that have a `ds` tag attached.

To tag a node, you can specify the `tags` argument:

```python
Node(func=add, inputs=["a", "b"], outputs="sum", name="adding_a_and_b", tags="node_tag")
```

Moreover, you can [tag all nodes in a `Pipeline`](./pipeline_introduction.md#how-to-tag-a-pipeline). If the pipeline definition contains the `tags=` argument, Kedro will attach the corresponding tag to every node within that pipeline.

To run a pipeline using a tag:

```bash
kedro run --tags=pipeline_tag
```

This runs the nodes found within the pipeline tagged with `pipeline_tag`.

!!! note
    Node or tag names must ONLY contain letters, digits, hyphens, underscores, and periods. Other symbols are not permitted.


## How to run a node

To run a node, you must instantiate its inputs. In this case, the node expects two inputs:

```python
adder_node.run(dict(a=2, b=3))
```

The output is as follows:

```console
Out[2]: {'sum': 5}
```

!!! note
    You can also call a node as a regular Python function: `adder_node(dict(a=2, b=3))`. This will call `adder_node.run(dict(a=2, b=3))` behind the scenes.

## How to use generator functions in a node

!!! warning
    This documentation section uses the `pandas-iris` starter that is unavailable in Kedro version 0.19.0 and beyond. The latest version of Kedro that supports `pandas-iris` is Kedro 0.18.14: install that or an earlier version to work through this example `pip install kedro==0.18.14`).

To check the version installed, type `kedro -V` in your terminal window.

[Generator functions](https://learnpython.org/en/Generators) were introduced with [PEP 255](https://www.python.org/dev/peps/pep-0255) and are a special kind of function in Python that returns lazy iterators. They are often used for lazy-loading or lazy-saving of data, which can be useful when dealing with large datasets that do not fit entirely into memory. In the context of Kedro, generator functions can be used in nodes to efficiently process and handle such large datasets.

### Set up the project

Set up a Kedro project using the legacy `pandas-iris` starter. Create the project with this command, assuming Kedro version 0.18.14:

```bash
kedro new --starter=pandas-iris --checkout=0.18.14
```

### Loading data with generators

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

### Saving data with generators
To use generators to save data lazily, you need do three things:
- Update the `make_prediction` function definition to use `yield` instead of `return`.
- Create a [custom dataset](../extend/how_to_create_a_custom_dataset.md) called `ChunkWiseCSVDataset`
- Update `catalog.yml` to use a newly created `ChunkWiseCSVDataset`.

Copy the following code to `nodes.py`. The main change is to use a new model `DecisionTreeClassifier` to make prediction by chunks in `make_predictions`.

<!--vale off-->
??? example "View code"
    ```python
    import logging
    from typing import Any, Dict, Tuple, Iterator, Generator
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
    ) -> Generator[pd.Series, None, None]:
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
<!--vale on-->

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

## How to add preview functions to nodes

!!! warning
    This functionality is experimental and may change or be removed in future releases. Experimental features follow the process described in  [`docs/about/experimental.md`](../about/experimental.md).

Preview function enables you to inject a callable which helps in debugging and monitoring. Instead of loading full datasets, preview functions can return lightweight summaries such as JSON metadata, table samples, charts, or diagrams.

### Overview

A preview function is a callable that returns a preview payload. Preview payloads can be:

- **JSON data** for metadata and statistics
- **Tables** for data samples
- **Charts** (Plotly) for visualizations
- **Diagrams** (Mermaid) for relationships and workflows
- **Images** for plots or visual outputs
- **Custom formats** with your own renderer

Preview functions are attached to nodes using the `preview_fn` argument and can be called using `node.preview()`.

### Basic usage

```python
from kedro.pipeline import node
from kedro.pipeline.preview_contract import JsonPreview

def preview_data_summary() -> JsonPreview:
    """Generate a JSON preview showing dataset statistics."""
    return JsonPreview(
        content={
            "num_rows": 1000,
            "num_columns": 5,
            "columns": ["id", "name", "age", "city", "score"],
        }
    )

def process_data(raw_data):
    # Your data processing logic
    return processed_data

# Create node with preview function
data_node = node(
    func=process_data,
    inputs="raw_data",
    outputs="processed_data",
    preview_fn=preview_data_summary,
    name="process_data_node"
)

# Generate preview
preview = data_node.preview()  # Returns JsonPreview object
preview_dict = preview.to_dict()  # Serialize for APIs/frontends
```

### Available preview types

Import the preview types you need:

```python
from kedro.pipeline.preview_contract import (
    JsonPreview,
    TablePreview,
    PlotlyPreview,
    MermaidPreview,
    ImagePreview,
    TextPreview,
    CustomPreview,
)
```

#### JSON preview

Use for metadata, statistics, or structured data:

```python
def preview_model_metrics() -> JsonPreview:
    return JsonPreview(
        content={
            "accuracy": 0.95,
            "precision": 0.93,
            "recall": 0.94,
            "f1_score": 0.935,
        }
    )
```

#### Table preview

Use for data samples or tabular summaries:

```python
def preview_sample_rows() -> TablePreview:
    return TablePreview(
        content=[
            {"name": "Alice", "age": 30, "city": "NYC"},
            {"name": "Bob", "age": 25, "city": "LA"},
            {"name": "Charlie", "age": 35, "city": "SF"},
        ]
    )
```

#### Plotly preview

Use for interactive charts and visualizations:

```python
def preview_distribution() -> PlotlyPreview:
    return PlotlyPreview(
        content={
            "data": [
                {
                    "x": ["A", "B", "C"],
                    "y": [10, 15, 13],
                    "type": "bar"
                }
            ],
            "layout": {
                "title": "Category Distribution",
                "xaxis": {"title": "Category"},
                "yaxis": {"title": "Count"}
            }
        }
    )
```

#### Mermaid preview

Use for diagrams, flowcharts, or process visualizations:

```python
def preview_pipeline_flow() -> MermaidPreview:
    return MermaidPreview(
        content="""
        graph LR
            A[Load Data] --> B[Clean Data]
            B --> C[Feature Engineering]
            C --> D[Train Model]
            D --> E[Evaluate]
        """
    )
```

#### Image preview

Use for plots, charts, or visual outputs (URL or data URI):

```python
def preview_correlation_matrix() -> ImagePreview:
    # Can return a URL
    return ImagePreview(
        content="https://example.com/correlation_matrix.png"
    )

    # Or a data URI for inline images
    # return ImagePreview(
    #     content="data:image/png;base64,iVBORw0KGgo..."
    # )
```

#### Text preview

Use for simple text summaries or logs:

```python
def preview_processing_log() -> TextPreview:
    return TextPreview(
        content="Processed 1,000 records\nRemoved 50 duplicates\nFilled 23 missing values"
    )
```

### Using preview functions with data context

Preview functions don't have access to node inputs or outputs directly. They're independent functions that you define. If you need to generate previews based on actual data, you have two options:

**Option 1: Use closure to capture context**

```python
def make_preview_fn(data_sample):
    """Create a preview function with captured context."""
    def preview_fn() -> TablePreview:
        return TablePreview(content=data_sample)
    return preview_fn

# In your pipeline creation
sample_data = [{"id": 1, "value": 100}, {"id": 2, "value": 200}]
node(
    func=process_data,
    inputs="data",
    outputs="result",
    preview_fn=make_preview_fn(sample_data)
)
```

**Option 2: Access datasets in preview function**

```python
from kedro.framework.project import pipelines
from kedro.framework.session import KedroSession

def preview_with_data_access() -> JsonPreview:
    """Preview function that loads data from catalog."""
    with KedroSession.create() as session:
        context = session.load_context()
        data = context.catalog.load("my_dataset")
        return JsonPreview(
            content={
                "row_count": len(data),
                "columns": list(data.columns),
            }
        )
```

### Adding metadata to previews

All preview types support optional metadata via the `meta` parameter:

```python
def preview_with_metadata() -> JsonPreview:
    return JsonPreview(
        content={"accuracy": 0.95},
        meta={
            "model_version": "v2.1",
            "training_date": "2024-01-15",
            "dataset": "train_split_2024"
        }
    )
```

### Custom preview types

For specialized rendering needs, use `CustomPreview`:

```python
def preview_custom_visualization() -> CustomPreview:
    return CustomPreview(
        renderer_key="my_custom_renderer",
        content={
            "type": "network_graph",
            "nodes": [...],
            "edges": [...]
        }
    )
```

The `renderer_key` identifies which frontend component should handle rendering this preview.

### Best practices

1. **Keep previews lightweight**: Preview functions should return summaries, not full datasets
2. **Make previews fast**: Avoid expensive computations in preview functions
3. **Use appropriate types**: Choose the preview type that best matches your data
4. **Add metadata**: Include context like timestamps, versions, or data sources
5. **Handle errors gracefully**: Wrap preview logic in try-except if needed
6. **Test preview functions**: Ensure they return valid preview objects

### Example: Complete node with preview

```python
from kedro.pipeline import node, Pipeline
from kedro.pipeline.preview_contract import TablePreview, JsonPreview
import pandas as pd

def train_model(training_data: pd.DataFrame) -> dict:
    """Train a model and return metrics."""
    # Training logic here
    return {
        "accuracy": 0.95,
        "loss": 0.05,
        "model_path": "models/model_v1.pkl"
    }

def preview_training_summary() -> JsonPreview:
    """Show model training summary."""
    return JsonPreview(
        content={
            "training_samples": 10000,
            "validation_samples": 2000,
            "epochs": 10,
            "status": "completed"
        },
        meta={
            "timestamp": "2024-01-15T10:30:00",
            "framework": "sklearn"
        }
    )

# Create pipeline
pipeline = Pipeline([
    node(
        func=train_model,
        inputs="training_data",
        outputs="model_metrics",
        preview_fn=preview_training_summary,
        name="train_model_node"
    )
])

# Later, generate preview
training_node = pipeline.nodes[0]
preview = training_node.preview()
print(preview.to_dict())
```

For more details on preview contract types, see the [API documentation][kedro.pipeline.preview_contract].
