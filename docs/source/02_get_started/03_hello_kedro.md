# A "Hello World" example

It is time to introduce the most basic elements of Kedro. We have split a small example into sections to discuss each of the concepts with code.

You can copy the example as one chunk of code from the bottom of this page.

```eval_rst
.. note::  We do not create a Kedro project in this first example, but illustrate the concepts within a single ``.py`` file.
```

## Node

A `node` is a Kedro concept. It is a wrapper for a Python function that names the inputs and outputs of that function. It is the building block of a pipeline. Nodes can be linked when the output of one node is the input of another.

Here, the `return_greeting` function is wrapped by a node called `return_greeting_node`, which has no inputs, and names a single output (`my_salutation`):

```python
from kedro.pipeline import node


# Prepare first node
def return_greeting():
    return "Hello"


return_greeting_node = node(func=return_greeting, inputs=None, outputs="my_salutation")
```

The `join_statements` function is wrapped by a node called `join_statements_node`, which names a single input (`my_salutation`) and a single output (`my_message`):

```python
# Prepare second node
def join_statements(greeting):
    return f"{greeting} Kedro!"


join_statements_node = node(
    join_statements, inputs="my_salutation", outputs="my_message"
)
```

Note that `my_salutation` is the output of `return_greeting_node` and also the input of `join_statements_node`.

## Pipeline

A pipeline organises the dependencies and execution order of a collection of nodes, and connects inputs and outputs while keeping your code modular. The pipeline determines the node execution order by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

In this example the pipeline executes `return_greeting_node` before it executes `join_statements_node`:

```python
from kedro.pipeline import Pipeline

# Assemble nodes into a pipeline
pipeline = Pipeline([return_greeting_node, join_statements_node])
```

## DataCatalog

A `DataCatalog` is a Kedro concept. It is the registry of all data sources that the project can use. It maps the names of node inputs and outputs as keys in a `DataSet`, which is a Kedro class that can be specialised for different types of data storage. Kedro uses a `MemoryDataSet` for data that is simply stored in-memory.

```python
from kedro.io import DataCatalog, MemoryDataSet

# Prepare a data catalog
data_catalog = DataCatalog({"my_salutation": MemoryDataSet()})
```

Kedro provides a [number of different built-in datasets](https://kedro.readthedocs.io/en/stable/kedro.extras.datasets.html#data-sets) for different file types and file systems so you don’t have to write the logic for reading/writing data.

## Runner

The Runner is an object that runs the pipeline. Kedro resolves the order in which the nodes are executed:

1.  Kedro first executes `return_greeting_node`. This runs `return_greeting`, which takes no input but outputs the string "Hello".
2.  The output string is stored in the `MemoryDataSet` named `my_salutation`.
3.  Kedro then executes the second node, `join_statements_node`. This loads the `my_salutation` dataset and injects it into the `join_statements` function.
4.  The function joins the input salutation with "Kedro!" to form the output string "Hello Kedro!"
5.  The output of the pipeline is returned in a dictionary with key `my_message`.

## Hello Kedro!

It's now time to stitch the code together. Here is the full example:

```python
"""Contents of hello_kedro.py"""
from kedro.io import DataCatalog, MemoryDataSet
from kedro.pipeline import node, Pipeline
from kedro.runner import SequentialRunner

# Prepare a data catalog
data_catalog = DataCatalog({"my_salutation": MemoryDataSet()})

# Prepare first node
def return_greeting():
    return "Hello"


return_greeting_node = node(return_greeting, inputs=None, outputs="my_salutation")

# Prepare second node
def join_statements(greeting):
    return f"{greeting} Kedro!"


join_statements_node = node(
    join_statements, inputs="my_salutation", outputs="my_message"
)

# Assemble nodes into a pipeline
pipeline = Pipeline([return_greeting_node, join_statements_node])

# Create a runner to run the pipeline
runner = SequentialRunner()

# Run the pipeline
print(runner.run(pipeline, data_catalog))
```
Then open a terminal and run the following command:

```bash
python hello_kedro.py
```

You should see `{'my_message': 'Hello Kedro!'}` printed to the console.
