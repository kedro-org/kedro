# TL;DR

This page summarises what you've learned about Kedro so far.

## [Logistics](install.md)
* Kedro can be used on Windows, macOS or Linux
* Installation prerequisites include Python 3.7+, `git` and `conda`
* You should install Kedro using `pip install kedro`

## [Kedro concepts](kedro_concepts.md)

* Kedro nodes are the building blocks of data processing pipelines. A node is a wrapper for a Python function that names the inputs and outputs of that function.
* A pipeline organises the dependencies and execution order of a collection of nodes.
* Kedro has a registry of all data sources the project can use called the Data Catalog. There is inbuilt support for various file types and file systems.
* Kedro projects follow a default template that uses specific folders to store datasets, notebooks, configuration and source code.


## [Kedro project creation](new_project.md)
* You can create a Kedro project:
    * with just the basic code: `kedro new`
    * or you can populate a new project with pre-built code, e.g. `kedro new --starter=pandas-iris` from a [range of starter projects](../kedro_project_setup/starters.md#list-of-official-starters)
* Once you've created a project, you need to navigate to its project folder; you can then install its dependencies: `pip install -r src/requirements.txt`
* To run the project: `kedro run`
* To visualise the project: `kedro viz`

## What's next?
* Next, you should work through the [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) for the hands-on experience. It illustrates how to build a working project, which includes creating nodes, registering pipelines, setting up the Data Catalog and adding dependencies.
* Following the tutorial, you'll learn how to [visualise a Kedro project](../visualisation/kedro-viz_visualisation.md) and learn more about [combining Kedro with a Jupyter notebook](../notebooks_and_ipython/kedro_and_notebooks.md).

## Useful links

* [Kedro on GitHub](https://github.com/kedro-org/kedro)
* [Join the Kedro community Slack channels](https://slack.kedro.org)
