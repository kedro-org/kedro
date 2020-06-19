# A "Hello World" example

In this example, we introduce the most basic elements of a Kedro project with a small amount of code to illustrate them.

A `kedro` project consists of the following main components:

```eval_rst
+--------------+-----------------------------------------------------------------------------+
| Component    | Description                                                                 |
+==============+=============================================================================+
| Node         | Wraps a Python function that typically executes some business logic,        |
|              | e.g. data cleaning, dropping columns, validation, model training, scoring.  |
+--------------+-----------------------------------------------------------------------------+
| Pipeline     | A pipeline takes care of the dependencies and execution order for a         |
|              | collection of nodes.                                                        |
+--------------+-----------------------------------------------------------------------------+
| Data Catalog | A collection of datasets that can be used to form the data pipeline.        |
|              | Each dataset provides :code:`load` and :code:`save` capabilities for        |
|              | a specific data type, e.g. :code:`pandas.CSVDataSet` loads and saves data   |
|              | to a CSV file.                                                              |
+--------------+-----------------------------------------------------------------------------+
| Runner       | An object that runs the pipeline using the specified data catalog.          |
|              | Kedro provides 3 runner types:                                              |
|              | :code:`SequentialRunner`, :code:`ParallelRunner` and :code:`ThreadRunner`.  |
+--------------+-----------------------------------------------------------------------------+
```

You can copy the code in one chunk from [the bottom of this page](#Hello_Kedro!), but we have split it into pieces in the following sections in order to discuss it step-by-step.

## Node

A `node` is a Kedro concept. It is a wrapper for a Python function that names the inputs and outputs of that function. It is the building block of a pipeline. Nodes can be linked when the output of one node is the input of another.

Here, the `return_greeting` function is wrapped by a node called `return_greeting_node`, which has no inputs, and names a single output(`my_salutation`):

```python
from kedro.pipeline import node

# Prepare nodes
def return_greeting():
    return "Hello"

return_greeting_node = node(return_greeting, inputs=None, outputs="my_salutation")
```

The `join_statements` function is wrapped by a node called `join_statements_node`, which names a single input (`my_salutation`) and a single output (`my_message`):

```python
def join_statements(greeting):
    return f"{greeting} Kedro!"

join_statements_node = node(join_statements, inputs="my_salutation", outputs="my_message")
```

Note that `my_salutation` is the output of `return_greeting_node` and also the input of `join_statements_node`.

## Pipeline

A pipeline organises the dependencies and execution order of a collection of nodes, and connect inputs and outputs while keeping your code modular. The pipeline determines the node execution order by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

In this example the pipeline executes `return_greeting_node` before it executes `join_statements_node`:

```python
from kedro.pipeline import Pipeline

# Assemble nodes into a pipeline
pipeline = Pipeline([
    return_greeting_node, join_statements_node
])
```

## DataCatalog

A `DataCatalog` is a Kedro concept. It is the registry of all data sources that the project can use. It maps the names of node inputs and outputs as keys in a `DataSet`, which is a Kedro class that can be specialised for different types of data storage. Kedro uses a `MemoryDataSet` for data that is simply stored in-memory.

```python
from kedro.io import DataCatalog, MemoryDataSet

# Prepare a data catalog
data_catalog = DataCatalog({
    "example_data": MemoryDataSet()
})
```

Kedro provides a [number of different built-in datasets](https://kedro.readthedocs.io/en/stable/kedro.extras.datasets.html#data-sets) for different file types and file systems so you don’t have to write the logic for reading/writing data.

## Hello Kedro!

It's now time to stitch the code together. Here is the full example:

```python
from kedro.io import DataCatalog, MemoryDataSet
from kedro.pipeline import node, Pipeline
from kedro.runner import SequentialRunner

# Prepare a data catalog
data_catalog = DataCatalog({
    "example_data": MemoryDataSet()
})


# Prepare nodes
def return_greeting():
    return "Hello"

return_greeting_node = node(return_greeting, inputs=None, outputs="my_salutation")

def join_statements(greeting):
    return f"{greeting} Kedro!"

join_statements_node = node(join_statements, inputs="my_salutation", outputs="my_message")


# Assemble nodes into a pipeline
pipeline = Pipeline([
    return_greeting_node, join_statements_node
])


# Create a runner
runner = SequentialRunner()

# Run the pipeline
runner.run(pipeline, data_catalog)
```

## Runner

The Runner runs the pipeline, and Kedro resolves the order in which the nodes are executed:

1.  Kedro first executes `return_greeting_node`.
2.  The node runs `return_greeting`, which takes no input but outputs the string "Hello".
3.  The output string is stored in the `MemoryDataSet` named `example_data` with the key `my_salutation`.
4.  Kedro then executes the second node, `join_statements_node`.
5.  The node loads `my_salutation` from `example_data` and injects it into the `join_statements` function.
6.  The function joins the input salutation with "Kedro!" to form the output string "Hello Kedro!"
7.  The output string is stored within `example_data` as `my_message`.
