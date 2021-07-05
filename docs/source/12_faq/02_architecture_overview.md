# Kedro architecture overview

```eval_rst
.. note::  This documentation is based on ``Kedro 0.17.4``. If you spot anything that is incorrect then please create an `issue <https://github.com/quantumblacklabs/kedro/issues>`_ or pull request.
```

![Kedro architecture diagram](../meta/images/kedro_architecture.png)

At a high level, Kedro consists of five main parts:

### Kedro project

As a data pipeline developer, you will interact with a Kedro project, which consists of:

* The **`conf/`** directory, which contains configuration for the project, such as data catalog configuration, parameters, etc.
* The **`src`** directory, which contains the source code for the project, including:
  * The **`pipeline`**  directory, which contains the source code for your pipeline.
  * **`settings.py`** file contains the settings for the project, such as library component registration, custom hooks registration, etc.
  * **`hooks.py`**, which contains custom [Hooks implementations](../07_extend_kedro/02_hooks) in the project, including both registration hooks and extension hooks.
  * **`cli.py`** file contains project specific CLI commands (e.g., `kedro run`, `kedro test`, etc.).
  * **`pipeline_registry.py`** file defines the project pipelines, i.e. pipelines that can be run using `kedro run --pipeline`.
  * **`__main__.py`** file serves as the main entry point of the project in [package mode](../03_tutorial/05_package_a_project.md#package-your-project).
* **`pyproject.toml`** identifies the project root by providing project metadata, including:
  * `package_name`: A valid Python package name for your project package
  * `project_name`: A human readable name for your project
  * `project_version`: Kedro version with which the project was generated

### Kedro starter

You can use a [Kedro starter](../02_get_started/06_starters) to generate a Kedro project that contains boilerplate  code. We maintain a set of [official starters](https://github.com/quantumblacklabs/kedro-starters/) but you can also use a custom starter of your choice.

### Kedro library

Kedro library consists of independent units, each responsible for one aspect of computation in a data pipeline:

* **`Config Loader`** provides utility to parse and load configuration defined in a Kedro project.
* **`Pipeline`** provides a collection of abstractions to model data pipelines.
* **`Runner`** provides an abstraction for different execution strategy of a data pipeline.
* **`I/O`** provides a collection of abstractions to handle I/O in a project, including `DataCatalog` and many `DataSet` implementations.

### Kedro framework

Kedro framework serves as the interface between a Kedro project and Kedro library components. The major building blocks of the Kedro framework include:

* **`Session`** is responsible for managing the lifecycle of a Kedro run.
* **`Context`** holds the configuration and Kedro's main functionality, and also serves as the main entry point for interactions with core library components.
* **`Hooks`** defines all hook specifications available to extend Kedro.
* **`CLI`** defines built-in Kedro CLI commands and utilities to load custom CLI commands from plugins.

### Kedro extension

You can also extend Kedro behaviour in your project using a Kedro extension, which can be a custom starter, a Python library with extra hooks implemenations, extra CLI commands such as [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz) or a custom library component implementation.
