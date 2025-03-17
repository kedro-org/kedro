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

{py:mod}`Kedro provides different built-in datasets <kedro-datasets:kedro_datasets>` for numerous file types and file systems, so you don’t have to write the logic for reading/writing data.

## Kedro project directory structure

One of the main advantages of working with Kedro projects is that they follow a default template that makes collaboration straightforward. Kedro uses semantic naming to set up a default project with specific folders to store datasets, notebooks, configuration and source code. We advise you to retain the default Kedro project structure to make it easy to share your projects with other Kedro users, although you can adapt the folder structure if you need to.

Starting from Kedro 0.19, when you create a new project with `kedro new`, you can customise the structure by selecting which tools to include. Depending on your choices, the resulting structure may vary. Below, we outline the default project structure when all tools are selected and give an example with no tools selected.

### Default Kedro project structure (all tools selected)

If you select all tools during project creation, your project structure will look like this:

```
project-dir          # Parent directory of the template
├── conf             # Project configuration files
├── data             # Local project data (not committed to version control)
├── docs             # Project documentation
├── notebooks        # Project-related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── src              # Project source code
├── tests            # Folder containing unit and integration tests
├── .gitignore       # Hidden file that prevents staging of unnecessary files to `git`
├── pyproject.toml   # Identifies the project root and contains configuration information
├── README.md        # Project README
├── requirements.txt # Project dependencies file
```

### Example Kedro project structure (no tools selected)

If you select no tools, the resulting structure will be simpler:

```
project-dir          # Parent directory of the template
├── conf             # Project configuration files
├── notebooks        # Project-related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── src              # Project source code
├── .gitignore       # Hidden file that prevents staging of unnecessary files to `git`
├── pyproject.toml   # Identifies the project root and contains configuration information
├── README.md        # Project README
├── requirements.txt # Project dependencies file
```

### Tool selection and resulting structure

During `kedro new`, you can select which [tools to include in your project](../starters/new_project_tools.md). Each tool adds specific files or folders to the project structure:

- **Lint (Ruff)**: Modifies the `pyproject.toml` file to include Ruff configuration settings for linting. It sets up `ruff` under `[tool.ruff]`, defines options like line length, selected rules, and ignored rules, and includes `ruff` as an optional `dev` dependency.
- **Test (Pytest)**: Adds a `tests` folder for storing unit and integration tests, helping to maintain code quality and ensuring that changes in the codebase do not introduce bugs. For more information about testing in Kedro, visit the [Automated Testing Guide](../development/automated_testing.md).
- **Log**: Allows specific logging configurations by including a `logging.yml` file inside the `conf` folder. For more information about logging customisation in Kedro, visit the [Logging Customisation Guide](../logging/index.md).
- **Docs (Sphinx)**: Adds a `docs` folder with a Sphinx documentation setup. This folder is typically used to generate technical documentation for the project.
- **Data Folder**: Adds a `data` folder structure for managing project data. The `data` folder contains multiple subfolders to store project data. We recommend you put raw data into `raw` and move processed data to other subfolders, as outlined [in this data engineering article](https://towardsdatascience.com/the-importance-of-layered-thinking-in-data-engineering-a09f685edc71).
- **PySpark**: Adds PySpark-specific configuration files.


### `conf`

The `conf` folder contains two subfolders for storing configuration information: `base` and `local`.

#### `conf/base`

Use the `base` subfolder for project-specific settings to share across different installations (for example, with other users).

The folder contains three files for the example, but you can add others as you require:

-   `catalog.yml` - [Configures the Data Catalog](../data/data_catalog.md#use-the-data-catalog-within-kedro-configuration) with the file paths and load/save configuration needed for different datasets
-   `logging.yml` - Uses Python's default [`logging`](https://docs.python.org/3/library/logging.html) library to set up logging (only added if the Log tool is selected).
-   `parameters.yml` - Allows you to define parameters for machine learning experiments, for example, train/test split and the number of iterations

#### `conf/local`

The `local` subfolder is specific to each user and installation and its contents is ignored by `git` (through inclusion in `.gitignore`).

Use the `local` subfolder for **settings that should not be shared**, such as access credentials, custom editor configuration, personal IDE configuration and other sensitive or personal content.

By default, Kedro creates one file, `credentials.yml`, in `conf/local`.

### `src`

This subfolder contains the project's source code.

### Customising your project structure

While the default Kedro structure is recommended for collaboration and standardisation, it is possible to adapt the folder structure if necessary. This flexibility allows you to tailor the project to your needs while maintaining a consistent and recognisable structure.

The only technical requirement when organising code is that the `pipeline_registry.py` and `settings.py` files must remain in the `<your_project>/src/<your_project>` directory, where they are created by default.

The `pipeline_registry.py` file must include a `register_pipelines()` function that returns a `dict[str, Pipeline]`, which maps pipeline names to their corresponding `Pipeline` objects.
