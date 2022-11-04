# Kedro concepts

<!-- TO DO -- add a bit more info here and design some graphics -->

It is time to introduce the most basic elements of Kedro. 

## Node

In Kedro, a node is a wrapper for a Python function that names the inputs and outputs of that function. Nodes are the building block of a pipeline, and the output of one node can be the input of another.

## Pipeline

A pipeline organises the dependencies and execution order of a collection of nodes, and connects inputs and outputs while keeping your code modular. The pipeline determines the **node execution order** by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

## Data Catalog

The Kedro Data Catalog is the registry of all data sources that the project can use that manages loading and saving of data. It maps the names of node inputs and outputs as keys in a `DataSet`, which is a Kedro class that can be specialised for different types of data storage. 

Kedro provides a [number of different built-in datasets](/kedro.extras.datasets) for different file types and file systems so you don’t have to write the logic for reading/writing data.

## Kedro project directory structure

Kedro projects follow a default structure that uses specific folders to store datasets, notebooks, configuration and source code. We advise you to retain the structure to make it easy to share your projects with other Kedro users, but when you create your own projects, you can adapt the folder structure if you need to.

The example project directory is set out as follows:

```
get-started         # Parent directory of the template
├── conf            # Project configuration files
├── data            # Local project data (not committed to version control)
├── docs            # Project documentation
├── logs            # Project output logs (not committed to version control)
├── notebooks       # Project related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── README.md       # Project README
├── setup.cfg       # Configuration options for `pytest` when doing `kedro test` and for the `isort` utility when doing `kedro lint`
└── src             # Project source code
```

Kedro also creates the following hidden files and folders:

```
get-started
├── .coveragerc     # Configuration file for the coverage reporting when doing `kedro test`
├── .gitignore      # Prevent staging of unnecessary files to `git`
└── pyproject.toml  # Identifies the project root and [contains configuration information](../faq/architecture_overview.md#kedro-project)
```

### `conf`

The `conf` folder contains two subfolders for storing configuration information: `base` and `local`.

#### `conf/base`

For project-specific settings to share across different installations (for example, with different users), you should use the `base` subfolder of `conf`.

The folder contains three files for the example, but you can add others as you require:

-   `catalog.yml` - [Configures the Data Catalog](../data/data_catalog.md#use-the-data-catalog-within-kedro-configuration) with the file paths and load/save configuration required for different datasets
-   `logging.yml` - Uses Python's default [`logging`](https://docs.python.org/3/library/logging.html) library to set up logging
-   `parameters.yml` - Allows you to define parameters for machine learning experiments e.g. train / test split and number of iterations

#### `conf/local`

The `local` subfolder of `conf` is used for **settings that should not be shared**, such as access credentials, custom editor configuration, personal IDE configuration and other sensitive or personal content. It is specific to user and installation. The contents of `conf/local` is ignored by `git` (through inclusion in `.gitignore`). By default, Kedro creates one file, `credentials.yml`, in `conf/local`.

### `data`

The `data` folder contains a number of subfolders to store project data. We recommend that you put raw data into `raw` and move processed data to other subfolders according to [data engineering convention](../faq/faq.md#what-is-data-engineering-convention).

### `src`

This subfolder contains the project's source code in one subfolder and another folder that you can use to add unit tests for your project. Projects are preconfigured to run tests using `pytest` when you call `kedro test` from the project's root directory
