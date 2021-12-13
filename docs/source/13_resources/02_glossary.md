# Kedro glossary


## Data Catalog
 The Data Catalog is Kedro's registry of all data sources available for use in the data pipeline. It manages loading and saving of data. The Data Catalog maps the names of node inputs and outputs as keys in a Kedro `DataSet`, which can be specialised for different types of data storage.

[Further information about the Data Catalog](../05_data/01_data_catalog)

## Data engineering vs Data science
Data engineering is the process of wrangling data into a clean and reliable state. Data wrangling is about taking a messy or unrefined source of data and turning it into something useful by parsing and cleaning it.

Data science extracts insights from data by using a combination of domain expertise, programming skills, and knowledge of mathematics and statistics. An old joke: "A data scientist is someone who knows more statistics than a computer scientist and more computer science than a statistician".

## Kedro
Kedro is an open-source Python framework for creating reproducible, maintainable and modular data science code. It applies software engineering best-practices to machine learning code, including modularity, separation of concerns and versioning.

[Introduction to Kedro](../01_introduction/01_introduction)

## `KedroContext`
A Python class that holds the configuration and Kedro’s main functionality.

API documentation for [`KedroContext`](/kedro.framework.context.KedroContext)

## `KedroSession`
A KedroSession allows you to manage the lifecycle of a Kedro run, persist runtime parameters and trace back runtime parameters, such as CLI command flags and environment variables.

[Further information about `KedroSession`](../04_kedro_project_setup/03_session)

## Kedro-Viz
You can use Kedro-Viz to visualise your Kedro data pipelines:

* See how your datasets and nodes are resolved in Kedro so that you can understand how your data pipeline is built
* Get a clear picture when you have lots of datasets and nodes by using tags to visualise sub-pipelines
* Search for nodes and datasets

[Further information from the Kedro-Viz repository](https://github.com/quantumblacklabs/kedro-viz) and [Kedro tutorial documentation](../03_tutorial/07_visualise_pipeline)

## Layers (data engineering convention)
According to [data engineering convention](../12_faq/01_faq.md#what-is-data-engineering-convention), a pipeline can be broken up into different layers according to how data is processed. This convention makes it easier to collaborate with other team members because everyone has an idea of what type of data cleaning or processing has happened.

Kedro-Viz makes it easy to [visualise these data processing stages](../03_tutorial/07_visualise_pipeline.md#visualise-layers) by adding a `layer` attribute to the datasets in the Data Catalog.

## Modular pipeline
_(See also [Pipeline](#pipeline))_

In many typical Kedro projects, a single (“main”) pipeline increases in complexity as the project evolves. To keep your project fit for purpose, you can create modular pipelines, which are logically isolated and can be reused. Modular pipelines are easier to develop, test and maintain, and are portable so they can be copied and reused between projects.

[Further information about modular pipelines](../06_nodes_and_pipelines/03_modular_pipelines)

## Node
A Kedro node is a wrapper for a Python function that names the inputs and outputs of that function. It is the building block of a pipeline. Nodes can be linked when the output of one node is the input of another.

[Further information about nodes](../06_nodes_and_pipelines/01_nodes)

## Node execution order
The node execution order is determined by resolving the input and output data dependencies between the nodes. The pipeline determines the node execution order and does not necessarily run the nodes in the order in which they are passed in.

## Pipeline
A Kedro pipeline organises the dependencies and execution order of a collection of nodes, and connects inputs and outputs. The pipeline determines the node execution order by resolving dependencies.

[Further information about pipelines](../06_nodes_and_pipelines/02_pipeline_introduction)

**_Chonky pipeline_**: _Chonky is generally used to describe animals that are plump, rounded or simply heavier than average. A chonky pipeline is, likewise, a pipeline that is more bulky than usual._

## Pipeline slicing
This is when you run a subset, or a ‘slice’ of a pipeline’s nodes. You can slice a pipeline in a variety of ways, such as:

* by providing specific inputs (`pipeline.from_inputs`)
* by specifying the nodes from which to start the pipeline (`pipeline.from_nodes`)
* by specifying a final node (`pipeline.to_nodes`)
* by tagging certain nodes (`pipeline.only_nodes_with_tags`)
* by specifying certain nodes (`pipeline.only_nodes`)

[Further information about pipeline slicing](../06_nodes_and_pipelines/05_slice_a_pipeline)

## Runner
Runners are different execution mechanisms to run pipelines with the specified data catalog.

* The sequential runner executes pipeline nodes one-by-one based on their dependencies
* The parallel runner allows for concurrency by use of multiprocessing
* The thread runner uses threading for concurrent execution

[Further information about runners](../06_nodes_and_pipelines/04_run_a_pipeline)

## Starters
Kedro starters are used to create projects that contain code to run as-is, or to adapt and extend. They provide pre-defined example code and configuration that can be reused. A Kedro starter is a [Cookiecutter template](https://cookiecutter.readthedocs.io/) that contains the boilerplate code for a Kedro project.

[Further information about Kedro starters](../02_get_started/06_starters)

## Tags
You can apply tags to nodes or pipelines as a means of filtering which are executed.

## Workflow dependencies
In Kedro, workflow dependencies are the packages that your project (the data and ML workflow) requires.
