# Kedro concepts

This page introduces the most basic elements of Kedro. You can find further information about these and more advanced Kedro concepts in the [Kedro glossary](../resources/glossary.md).

You may prefer to skip to the next section to [create a Kedro project for hands-on Kedro experience](./new_project.md).

## Summary

* Kedro nodes are the building blocks of pipelines. A node is a wrapper for a Python function that names the inputs and outputs of that function.
* A pipeline organises the dependencies and execution order of a collection of nodes.
* Kedro has a registry of all data sources the project can use called the Data Catalog. There is inbuilt support for various file types and file systems.
* Kedro projects follow a default template that uses specific folders to store datasets, notebooks, configuration and source code.


## Node

In Kedro, a node is a wrapper for a [pure Python function](../resources/glossary.md#node) that names the inputs and outputs of that function. Nodes are the building block of a pipeline, and the output of one node can be the input of another.

Here are two simple nodes as an example:

```python
from kedro.pipeline import node

# First node
def return_greeting():
    return "Hello"


return_greeting_node = node(func=return_greeting, inputs=None, outputs="my_salutation")

# Second node
def join_statements(greeting):
    return f"{greeting} Kedro!"


join_statements_node = node(
    join_statements, inputs="my_salutation", outputs="my_message"
)
```

## Pipeline

A pipeline organises the dependencies and execution order of a collection of nodes and connects inputs and outputs while keeping your code modular. The pipeline determines the **node execution order** by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

Here is a pipeline comprised of the nodes shown above:

```python
from kedro.pipeline import pipeline

# Assemble nodes into a pipeline
greeting_pipeline = pipeline([return_greeting_node, join_statements_node])
```

## Data Catalog

The Kedro Data Catalog is the registry of all data sources that the project can use to manage loading and saving data. It maps the names of node inputs and outputs as keys in a `DataCatalog`, a Kedro class that can be specialised for different types of data storage.

[Kedro provides different built-in datasets](/kedro_datasets) for numerous file types and file systems, so you don’t have to write the logic for reading/writing data.

## Kedro project directory structure

One of the main advantages of working with Kedro projects is that they follow a default template that makes collaboration straightforward. Kedro uses semantic naming to set up a default project with specific folders to store datasets, notebooks, configuration and source code. We advise you to retain the default Kedro project structure to make it easy to share your projects with other Kedro users, although you can adapt the folder structure if you need to.

The default Kedro project structure is as follows:

```
project-dir         # Parent directory of the template
├── .gitignore      # Hidden file that prevents staging of unnecessary files to `git`
├── conf            # Project configuration files
├── data            # Local project data (not committed to version control)
├── docs            # Project documentation
├── notebooks       # Project-related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── pyproject.toml  # Identifies the project root and contains configuration information
├── README.md       # Project README
└── src             # Project source code
```

### `conf`

The `conf` folder contains two subfolders for storing configuration information: `base` and `local`.

#### `conf/base`

Use the `base` subfolder for project-specific settings to share across different installations (for example, with other users).

The folder contains three files for the example, but you can add others as you require:

-   `catalog.yml` - [Configures the Data Catalog](../data/data_catalog.md#use-the-data-catalog-within-kedro-configuration) with the file paths and load/save configuration needed for different datasets
-   `logging.yml` - Uses Python's default [`logging`](https://docs.python.org/3/library/logging.html) library to set up logging
-   `parameters.yml` - Allows you to define parameters for machine learning experiments, for example, train/test split and the number of iterations

#### `conf/local`

The `local` subfolder is specific to each user and installation and its contents is ignored by `git` (through inclusion in `.gitignore`).

Use the `local` subfolder for **settings that should not be shared**, such as access credentials, custom editor configuration, personal IDE configuration and other sensitive or personal content.

By default, Kedro creates one file, `credentials.yml`, in `conf/local`.

### `data`

The `data` folder contains multiple subfolders to store project data. We recommend you put raw data into `raw` and move processed data to other subfolders according to the [commonly accepted data engineering convention](https://towardsdatascience.com/the-importance-of-layered-thinking-in-data-engineering-a09f685edc71).

### `src`

This subfolder contains the project's source code.
