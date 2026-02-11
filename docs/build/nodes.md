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

Preview function enables you to inject a callable which helps in debugging and monitoring. Instead of loading full datasets, preview functions can return lightweight summaries, code snippets, charts, or diagrams.

### Overview

A preview function is a callable that returns a preview payload. Preview payloads can be:

- **Summaries** (Text) for logs and code snippets
- **Diagrams** (Mermaid) for relationships and workflows
- **Images** for plots or visual outputs
- **Custom formats** with your own renderer

Preview functions are attached to nodes using the `preview_fn` argument and can be called using `node.preview()`.

### Basic usage

```python
from kedro.pipeline import node, Pipeline
from kedro.pipeline.preview_contract import MermaidPreview
import pandas as pd

def train_model(training_data: pd.DataFrame) -> dict:
    return {
        "accuracy": 0.95,
        "loss": 0.05,
        "model_path": "models/model_v1.pkl"
    }

def preview_training_model() -> MermaidPreview:
    return MermaidPreview(
        content="""
        flowchart TD
            A[Training Started] --> B[Load Dataset]
            B --> C[Training Samples: 10,000]
            B --> D[Validation Samples: 2,000]
            C --> E[Train Model]
            D --> E
            E --> F[Epochs: 10]
            F --> G[Status: Completed]
        """,
        meta={
            "timestamp": "2024-01-15T10:30:00",
            "framework": "sklearn"
        }
    )

pipeline = Pipeline(
    [
        node(
            func=train_model,
            inputs="training_data",
            outputs="model_metrics",
            # injecting a node preview callable
            preview_fn=preview_training_model,
            name="train_model_node",
        )
    ]
)

# Get the node
training_node = next(n for n in pipeline.nodes)

# Generate preview
preview = training_node.preview() # Returns MermaidPreview object
preview_dict = preview.to_dict() # Serialise for APIs/frontends

```

### Available preview types

Import the preview types you need:

```python
from kedro.pipeline.preview_contract import (
    MermaidPreview,
    ImagePreview,
    TextPreview,
    CustomPreview,
)
```

#### Mermaid preview

Use for diagrams, flowcharts, or process visualisations:

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

You can customise how Mermaid diagrams are rendered in Kedro-Viz by providing a configuration object in the `meta` parameter. This allows you to control layout, styling, text wrapping, and other rendering options:

```python
def generate_mermaid_preview() -> MermaidPreview:
    """Generate a Mermaid diagram with custom configuration.

    This example demonstrates how to customize both the Mermaid rendering
    configuration and the text styling for node labels.
    """
    diagram = """graph TD
    A[Raw Data] -->|Ingest| B(Typed Data)
    B --> C{Quality Check}
    C -->|Pass| D[Clean Data]
    C -->|Fail| E[Error Log]
    D --> F[Feature Engineering]
    F --> G[Model Training]
    G --> H[Predictions]

    style A fill:#e1f5ff
    style D fill:#c8e6c9
    style E fill:#ffcdd2
    style H fill:#fff9c4"""

    # Customize Mermaid rendering configuration
    # NOTE: On Kedro-Viz, this configuration will be
    # merged with sensible defaults
    custom_config = {
        "securityLevel": "strict",  # Security level: 'strict', 'loose', 'antiscript'
        "flowchart": {
            "wrappingWidth": 300,   # Text wrapping threshold (default: 250)
            "nodeSpacing": 60,      # Horizontal space between nodes (default: 50)
            "rankSpacing": 60,      # Vertical space between levels (default: 50)
            "curve": "basis",       # Edge curve style: 'basis', 'linear', 'step'
        },
        "themeVariables": {
            "fontSize": "16px",     # Font size for labels (default: '14px')
        },
        # CSS styling for text nodes
        "textStyle": {
            "padding": "6px",           # Internal padding in nodes (default: '4px')
            "lineHeight": "1.3",        # Line height for wrapped text (default: '1.2')
            "textAlign": "center",      # Text alignment (default: 'center')
        }
    }

    return MermaidPreview(content=diagram, meta=custom_config)

node(
    func=process_data,
    inputs="raw_data",
    outputs="processed_data",
    preview_fn=generate_mermaid_preview,
    name="data_processing_node",
)
```

For a complete list of available Mermaid configuration options, see the [Mermaid configuration schema documentation](https://mermaid.js.org/config/schema-docs/config.html).

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

Use for text summaries or logs:

```python
def preview_processing_log() -> TextPreview:
    return TextPreview(
        content="Processed 1,000 records\nRemoved 50 duplicates\nFilled 23 missing values"
    )
```

You can also display code snippets with syntax highlighting in Kedro-Viz by specifying the language in the `meta` parameter:

```python
def generate_code_preview() -> TextPreview:
    """Generate a code preview with syntax highlighting."""
    code = """def calculate_metrics(data):
    \"\"\"Calculate key performance metrics.\"\"\"
    import pandas as pd

    metrics = {
        'mean': data.mean(),
        'median': data.median(),
        'std': data.std()
    }

    return pd.DataFrame(metrics)

# Example usage
result = calculate_metrics(my_dataframe)
print(result)"""

    return TextPreview(content=code, meta={"language": "python"})

node(
    func=calculate_metrics,
    inputs="data",
    outputs="metrics",
    preview_fn=generate_code_preview,
    name="metrics_calculation_node",
)
```

The `meta` parameter accepts a `language` key to specify the programming language for syntax highlighting. Kedro-Viz supports `python`, `javascript`, and `yaml` highlighting.

#### Custom preview

For specialised rendering needs, use `CustomPreview`:

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

### Adding metadata to previews

All preview types support optional metadata with `meta` parameter. The `meta` parameter serves two purposes:

1. **General metadata**: Add contextual information like versions, timestamps, or data sources
2. **Rendering configuration**: Control how previews are displayed in Kedro-Viz (for example, Mermaid diagram layout, syntax highlighting)

**Example: Adding general metadata**

```python
def preview_processing_log() -> TextPreview:
    return TextPreview(
        content="Processed 1,000 records\nRemoved 50 duplicates\nFilled 23 missing values",
        meta={"created_by": "admin"}
    )
```

**Example: Rendering configuration**

For specific rendering configurations, see:

- [Mermaid preview](#mermaid-preview) - Customise diagram layout and styling
- [Text preview](#text-preview) - Enable code syntax highlighting

### Using preview functions with data context

Preview functions don't have access to node inputs or outputs directly. They're independent functions that you define. If you need to generate previews based on actual data, you can use closures or access datasets within the preview function.

**Use closure to capture context**

```python
def make_preview_fn(graph_diagram):
    """Create a preview function with captured context."""
    def preview_fn() -> MermaidPreview:
        return MermaidPreview(content=graph_diagram)
    return preview_fn

# In your pipeline creation
sample_diagram = """graph TD
    A[Raw Data] -->|Ingest| B(Typed Data)
    B --> C{Quality Check}
    C -->|Pass| D[Clean Data]
    C -->|Fail| E[Error Log]
    D --> F[Feature Engineering]
    F --> G[Model Training]
    G --> H[Predictions]

    style A fill:#e1f5ff
    style D fill:#c8e6c9
    style E fill:#ffcdd2
    style H fill:#fff9c4"""

node(
    func=process_data,
    inputs="data",
    outputs="result",
    preview_fn=make_preview_fn(sample_diagram)
)
```

### Best practices

1. **Keep previews lightweight**: Preview functions should return summaries, not full datasets. For dataset previews, use the [dataset preview feature](https://docs.kedro.org/projects/kedro-viz/en/stable/preview_datasets/) instead of node previews.
2. **Make previews fast**: Avoid expensive computations in preview functions
3. **Use appropriate types**: Choose the preview type that best matches your data
4. **Add metadata**: Include context like timestamps, versions, or data sources
5. **Handle errors**: Wrap preview logic in try-except if needed
6. **Test preview functions**: Ensure they return valid preview objects
