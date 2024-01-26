# Kedro glossary


## Data Catalog
 The Data Catalog is Kedro's registry of all data sources available for use in the data pipeline. It manages loading and saving of data. The Data Catalog maps the names of node inputs and outputs as keys in a Kedro dataset, which can be specialised for different types of data storage.

[Further information about the Data Catalog](../data/data_catalog.md)

## Data engineering vs Data science
Data engineering is the process of wrangling data into a clean and reliable state. Data wrangling is about taking a messy or unrefined source of data and turning it into something useful by parsing and cleaning it.

Data science extracts insights from data by using a combination of domain expertise, programming skills, and knowledge of mathematics and statistics. An old joke: "A data scientist is someone who knows more statistics than a computer scientist and more computer science than a statistician".

## Kedro
Kedro is an open-source Python framework for creating reproducible, maintainable and modular data science code. It applies software engineering best-practices to machine learning code, including modularity, separation of concerns and versioning.

[Introduction to Kedro](../introduction/index.md)

## `KedroContext`
A Python class that holds the configuration and Kedro’s main functionality.

API documentation for [`KedroContext`](/api/kedro.framework.context.KedroContext)

## `KedroSession`
A KedroSession allows you to manage the lifecycle of a Kedro run, persist runtime parameters and trace back runtime parameters, such as CLI command flags and environment variables.

[Further information about `KedroSession`](../kedro_project_setup/session.md)

## Kedro-Viz
You can use Kedro-Viz to visualise your Kedro data pipelines:

* See how your datasets and nodes are resolved in Kedro so that you can understand how your data pipeline is built
* Get a clear picture when you have lots of datasets and nodes by using tags to visualise sub-pipelines
* Search for nodes and datasets

[Further information from the Kedro-Viz repository](https://github.com/kedro-org/kedro-viz) and {doc}`Kedro-Viz documentation<kedro-viz:kedro-viz_visualisation>`.

## Layers (data engineering convention)
According to [common data engineering convention](https://towardsdatascience.com/the-importance-of-layered-thinking-in-data-engineering-a09f685edc71), a pipeline can be broken up into different layers according to how data is processed. This convention makes it easier to collaborate with other team members because everyone has an idea of what type of data cleaning or processing has happened.

Kedro-Viz makes it easy to visualise these data processing stages by adding a `layer` attribute to the `kedro-viz` section within the `metadata` of the datasets in the Data Catalog.

## Modular pipeline
_(See also [Pipeline](#pipeline))_

In many typical Kedro projects, a single (“main”) pipeline increases in complexity as the project evolves. To keep your project fit for purpose, you can create modular pipelines, which are logically isolated and can be reused. Modular pipelines are easier to develop, test and maintain, and are portable so they can be copied and reused between projects.

[Further information about modular pipelines](../nodes_and_pipelines/modular_pipelines.md)

## Node
A Kedro node is a wrapper for a pure Python function that names the inputs and outputs of that function.

(A [pure function](https://realpython.com/python-functional-programming/#what-is-functional-programming) is a one whose output value follows solely from its input values, without any observable side effects such as changes to state or mutable data).

Nodes are the building block of a pipeline. Nodes can be linked when the output of one node is the input of another.

[Further information about nodes](../nodes_and_pipelines/nodes.md)

## Node execution order
The node execution order is determined by resolving the input and output data dependencies between the nodes. The pipeline determines the node execution order and does not necessarily run the nodes in the order in which they are passed in.

## Pipeline
A Kedro pipeline organises the dependencies and execution order of a collection of nodes, and connects inputs and outputs. The pipeline determines the node execution order by resolving dependencies.

[Further information about pipelines](../nodes_and_pipelines/pipeline_introduction.md)

**_Chonky pipeline_**: _Chonky is generally used to describe animals that are plump, rounded or simply heavier than average. A chonky pipeline is, likewise, a pipeline that is more bulky than usual._

## Pipeline slicing
This is when you run a subset, or a ‘slice’ of a pipeline’s nodes. You can slice a pipeline in a variety of ways, such as:

* by providing specific inputs (`pipeline.from_inputs`)
* by specifying the nodes from which to start the pipeline (`pipeline.from_nodes`)
* by specifying a final node (`pipeline.to_nodes`)
* by tagging certain nodes (`pipeline.only_nodes_with_tags`)
* by specifying certain nodes (`pipeline.only_nodes`)

[Further information about pipeline slicing](../nodes_and_pipelines/slice_a_pipeline.md)

## Runner
Runners are different execution mechanisms to run pipelines with the specified data catalog.

* The sequential runner executes pipeline nodes one-by-one based on their dependencies
* The parallel runner allows for concurrency by use of multiprocessing
* The thread runner uses threading for concurrent execution

[Further information about runners](../nodes_and_pipelines/run_a_pipeline.md)

## Starters
Kedro starters are used to create projects that contain code to run as-is, or to adapt and extend. They provide pre-defined example code and configuration that can be reused. A Kedro starter is a [Cookiecutter template](https://cookiecutter.readthedocs.io/) that contains the boilerplate code for a Kedro project.

[Further information about Kedro starters](../starters/starters.md)

## Tags
You can apply tags to nodes or pipelines as a means of filtering which are executed.

## Workflow dependencies
In Kedro, workflow dependencies are the packages that your project (the data and ML workflow) requires.
