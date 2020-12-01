## Overview

This is a bare minimum setup for you to use a core component of Kedro in the exploratory phase of a project. Specifically, it enables you to use Kedro to configure and explore data sources in Jupyter notebook through the [DataCatalog](https://kedro.readthedocs.io/en/stable/05_data/01_data_catalog.html) feature.
Later on, you can build a full pipeline using the same configuration.

The project was generated using `Kedro {{ cookiecutter.kedro_version }}`.

## Prerequisites

To use this project, you need to have `kedro[pandas.CSVDataSet]` and `jupyter` installed. They are included in the `requirements.txt` file, which can be installed with `pip`:

```bash
pip install -r requirements.txt
```

## The example notebook

After installing the requirements, you can launch Jupyter Notebook server as normal with:

```bash
jupyter notebook
```

At the root directory, you will find an example notebook showing how to instantiate the `DataCatalog` and interact with the included example dataset.
You can edit the [conf/catalog.yml](./conf/base/catalog.yml) file to add more datasets to the `DataCatalog` for further exploration. To see more examples on how to use the `DataCatalog`, please visit the [DataCatalog documentation](https://kedro.readthedocs.io/en/latest/05_data/01_data_catalog.html).

## Transition to a full Kedro project

After configuring and exploring the data sources in Jupyter notebooks, you can transition to a full Kedro project through the following steps:

1. Create a new empty Kedro project in a new directory

```bash
kedro new
```

Let's assume that the new project is created at `/path/to/your/project`.

2. Copy the `conf/` and `data/` directories over to the new project

```
cp -fR {conf,data} `/path/to/your/project`
```

Congratulations! You now have a Kedro project setup with a fully functional `DataCatalog`. You can then explore the documentation on how to write [nodes and pipelines](https://kedro.readthedocs.io/en/latest/06_nodes_and_pipelines/01_nodes.html) to process this data.

### Limitation

If you stick with this project structure without transitioning to a full project, you will only be able to use Kedro's library components such as the `DataCatalog`, `Node` and `Pipeline` manually. You won't be able to use features available in a full Kedro project, including project-based CLI commands such as `kedro run`.
