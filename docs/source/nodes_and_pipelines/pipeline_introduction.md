# Pipelines

A pipeline is a set of [Nodes](./nodes.md) that will be automatically resolved after pipeline creation to determine the node execution order based on outputs and inputs of each node.

Technically {py:class}`~kedro.pipeline.Pipeline` is a python class that could be created using {py:class}`~kedro.pipeline.modular_pipeline.pipeline` method, based on Nodes or other Pipelines(in that case all nodes from that pipeline will be used).

Most important about kedro pipelines:
- [How to create a simple pipeline](#how-to-create-a-simple-pipeline)
- [Create a new blank pipeline with kedro pipeline create command](#create-a-new-blank-pipeline-with-the-kedro-pipeline-create-command)
- [Pipeline creation structure](#pipeline-creation-structure)
- [Key Pipeline methods and operations](#key-pipeline-methods-and-operations)
- [Bad pipelines - rules](#bad-pipelines)
- [Custom new pipeline templates](#custom-new-pipeline-templates)

## How to create a simple pipeline

In the following example, we construct a simple pipeline that computes the variance of a set of numbers. In practice, pipelines can use more complicated node definitions, and the variables they use usually correspond to entire datasets:

```python
from kedro.pipeline import pipeline, node

def mean(xs, n):
    return sum(xs) / n

def mean_sos(xs, n):
    return sum(x**2 for x in xs) / n

def variance(m, m2):
    return m2 - m * m


variance_pipeline = pipeline(
    [
        node(len, "xs", "n"),
        node(mean, ["xs", "n"], "m", name="mean_node"),
        node(mean_sos, ["xs", "n"], "m2", name="mean_sos"),
        node(variance, ["m", "m2"], "v", name="variance_node"),
    ]
)
```


## Create a new blank pipeline with the `kedro pipeline create` command

When managing your Kedro project, we recommend organising your pipelines separately to achieve modularity. This approach allows for easy copying and reuse of pipelines within and between projects. Simply put: one pipeline, one folder. To help with that, you can use the following command (the pipeline name must adhere to [Python convention](https://realpython.com/python-pep8/#naming-conventions)):


```bash
kedro pipeline create <pipeline_name>
```

After running this command, a new pipeline with boilerplate folders and files will be created in your project. For your convenience, Kedro gives you a pipeline-specific `nodes.py`, `pipeline.py`, parameters file and appropriate `tests` structure. It also adds the appropriate `__init__.py` files. You can see the generated folder structure below:


```text
├── conf
│   └── base
│       └── parameters_{{pipeline_name}}.yml  <-- Pipeline-specific parameters
└── src
    ├── my_project
    │   ├── __init__.py
    │   └── pipelines
    │       ├── __init__.py
    │       └── {{pipeline_name}}      <-- This folder defines the pipeline
    │           ├── __init__.py        <-- So that Python treats this pipeline as a module
    │           ├── nodes.py           <-- To declare your nodes
    │           └── pipeline.py        <-- To structure the pipeline itself
    └── tests
        ├── __init__.py
        └── pipelines
            ├── __init__.py
            └── {{pipeline_name}}      <-- Pipeline-specific tests
                ├── __init__.py
                └── test_pipeline.py

```

If you want to do the reverse and remove that pipeline, you can use `kedro pipeline delete <pipeline_name>` to do so or have a look to all [project-specific CLI commands list](../development/commands_reference.md#kedro-commands).
```{note}
For the full list of available CLI options, you can always run `kedro pipeline create --help` for more information.
```

## Pipeline creation structure

After creating the pipeline with `kedro pipeline create`, you will find template code in `pipeline.py` that you need to fill with your actual pipeline code:

```python
# src/my_project/pipelines/{{pipeline_name}}/pipeline.py
from kedro.pipeline import Pipeline, pipeline

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([])
```
Here, you are creating a function that returns a `Pipeline` class instance with the help of the `pipeline` function. We recommend putting your pipeline creation code into a function because it allows to achieve:
- Modularity: you can easily reuse this logic across different parts of your project.
- Parameterisation: with `create_pipeline(**kwargs)` you can pass different parameters to the pipeline creation function, enabling dynamic pipeline creation
- Testing: you can write unit tests for the create_pipeline function to ensure that it correctly constructs the pipeline

Before filling `pipeline.py` with nodes, we recommend storing all node functions in `nodes.py`. From our previous example, we should put:

```python
# src/my_project/pipelines/{{pipeline_name}}/nodes.py
def mean(xs, n):
    return sum(xs) / n

def mean_sos(xs, n):
    return sum(x**2 for x in xs) / n

def variance(m, m2):
    return m2 - m * m
```

```python
# src/my_project/pipelines/{{pipeline_name}}/pipelines.py
from kedro.pipeline import Pipeline, pipeline, node

from .nodes import mean, mean_sos, variance
# Import node functions from nodes.py located in the same folder

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
    [
        node(len, "xs", "n"),
        node(mean, ["xs", "n"], "m", name="mean_node", tags = "tag1"),
        node(mean_sos, ["xs", "n"], "m2", name="mean_sos", tags = ["tag1", "tag2"]),
        node(variance, ["m", "m2"], "v", name="variance_node"),
    ], # A list of nodes and pipelines combined into a new pipeline
    tags = "tag3", # Optional, each pipeline node will be tagged
    namespace = "", # Optional
    inputs = {}, # Optional
    outputs = {}, # Optional
    parameters = {}, # Optional
```
Here it was shown that pipeline creation function have few optional parameters, you can use:
- tags on a pipeline level to apply them for all nodes inside of pipeline
- namespace, inputs, outputs and parameters to reuse pipelines. More about that you can find [here](modular_pipelines.md)

## Key Pipeline methods and operations

You can:
- [use `describe` to discover what nodes are part of the pipeline](#use-describe-to-discover-what-nodes-are-part-of-the-pipeline)
- [merge multiple pipelines](#how-to-merge-multiple-pipelines)
- [receive information about the nodes in a pipeline](#information-about-the-nodes-in-a-pipeline)
- [receive information about pipeline inputs and outputs](#information-about-pipeline-inputs-and-outputs)

### Use `describe` to discover what nodes are part of the pipeline

```python
print(variance_pipeline.describe())
```

The output is as follows:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean_node
mean_sos
variance_node

Outputs: v
##################################
```

### How to merge multiple pipelines

You can merge multiple pipelines as shown below. Note that, in this case, `pipeline_de` and `pipeline_ds` are expanded to a list of their underlying nodes and these are merged together:

```python
pipeline_de = pipeline([node(len, "xs", "n"), node(mean, ["xs", "n"], "m")])

pipeline_ds = pipeline(
    [node(mean_sos, ["xs", "n"], "m2"), node(variance, ["m", "m2"], "v")]
)

last_node = node(print, "v", None)

pipeline_all = pipeline([pipeline_de, pipeline_ds, last_node])
print(pipeline_all.describe())
```

The output is as follows:

```console
#### Pipeline execution order ####
Name: None
Inputs: xs

len([xs]) -> [n]
mean([n,xs]) -> [m]
mean_sos([n,xs]) -> [m2]
variance([m,m2]) -> [v]
print([v]) -> None

Outputs: None
##################################
```


### Information about the nodes in a pipeline

Pipelines provide access to their nodes in a topological order to enable custom functionality, e.g. pipeline visualisation. Each node has information about its inputs and outputs:

<summary><b>Click to expand</b></summary>

```python
nodes = variance_pipeline.nodes
nodes
```

The output is as follows:

```python
[
    Node(len, "xs", "n", None),
    Node(mean, ["xs", "n"], "m", "mean_node"),
    Node(mean_sos, ["xs", "n"], "m2", "mean_sos"),
    Node(variance, ["m", "m2"], "v", "variance node"),
]
```

To find out about the inputs:

```python
nodes[0].inputs
```

You should see the following:

```python
["xs"]
```

### Information about pipeline inputs and outputs
In a similar way to the above, you can use `inputs()` and `outputs()` to check the inputs and outputs of a pipeline:

```python
variance_pipeline.inputs()
```

Gives the following:

```console
Out[7]: {'xs'}
```

```python
variance_pipeline.outputs()
```

Displays the output:

```console
Out[8]: {'v'}
```


## Bad pipelines

A pipelines can usually readily resolve its dependencies. In some cases, resolution is not possible. In this case, the pipeline is not well-formed.

### Pipeline with bad nodes

In this case, we have a pipeline consisting of a single node with no input and output:


```python
try:
    pipeline([node(lambda: print("!"), None, None)])
except Exception as e:
    print(e)
```

Gives the following output:

```console
Invalid Node definition: it must have some `inputs` or `outputs`.
Format should be: node(function, inputs, outputs)
```


### Pipeline with circular dependencies

For every two variables where the first depends on the second, there must not be a way in which the second also depends on the first, otherwise, a circular dependency will prevent us from compiling the pipeline.

The first node captures the relationship of how to calculate `y` from `x` and the second captures the relationship of how to calculate `x` knowing `y`. The pair of nodes cannot co-exist in the same pipeline:


```python
try:
    pipeline(
        [
            node(lambda x: x + 1, "x", "y", name="first node"),
            node(lambda y: y - 1, "y", "x", name="second node"),
        ]
    )
except Exception as e:
    print(e)
```

The output is as follows:

```console
Circular dependencies exist among these items: ['first node: <lambda>([x]) -> [y]', 'second node: <lambda>([y]) -> [x]']
```

### Pipeline nodes named with the dot notation
Nodes named with dot notation may behave strangely.

```python
pipeline([node(lambda x: x, inputs="input1kedro", outputs="output1.kedro")])
```

Nodes that are created with input or output names that contain `.` risk a disconnected pipeline or improperly-formatted Kedro structure.

This is because `.` has a special meaning internally and indicates a namespace pipeline. In the example, the outputs segment should be disconnected as the name implies there is an "output1" namespace pipeline. The input is not namespaced, but the output is via its dot notation. This leads to Kedro processing each separately. For this example, a better approach would've been writing both as `input1_kedro` and `output1_kedro`.

We recommend use of characters like `_` instead of `.` as name separators.


## Custom new pipeline templates

If you want to generate a pipeline with a custom Cookiecutter template, you can save it in `<project_root>/templates/pipeline`.
The `kedro pipeline create` command will pick up the custom template in your project as the default. You can also specify the path to your custom
Cookiecutter pipeline template with the `--template` flag like this:
```bash
kedro pipeline create <pipeline_name> --template <path_to_template>
```
A template folder passed to `kedro pipeline create` using the `--template` argument will take precedence over any local templates.
Kedro supports having a single pipeline template in your project. If you need to have multiple pipeline templates, consider saving them in a
separate folder and pointing to them with the `--template` flag.

### Creating custom templates

It is your responsibility to create functional Cookiecutter templates for custom pipelines. Please ensure you understand the basic structure of a pipeline. Your template should render to a valid, importable Python module containing a
`create_pipeline` function at the top level that returns a `Pipeline` object. You will also need appropriate
`config` and `tests` subdirectories that will be copied to the project `config` and `tests` directories when the pipeline is created.
The `config` and `tests` directories need to follow the same layout as in the default template and cannot
be customised, although the contents of the parameters and actual test file can be changed. File and folder names or structure
do not matter beyond that and can be customised according to your needs. You can use [the
default template that Kedro](https://github.com/kedro-org/kedro/tree/main/kedro/templates/pipeline) uses as a starting point.

Pipeline templates are rendered using [Cookiecutter](https://cookiecutter.readthedocs.io/), and must also contain a `cookiecutter.json`
See the [`cookiecutter.json` file in the Kedro default template](https://github.com/kedro-org/kedro/tree/main/kedro/templates/pipeline/cookiecutter.json) for an example.
It is important to note that if you are embedding your custom pipeline template within a
Kedro starter template, you must tell Cookiecutter not to render this template when creating a new project from the starter. To do this,
you must add [`_copy_without_render: ["templates"]`](https://cookiecutter.readthedocs.io/en/stable/advanced/copy_without_render.html) to the `cookiecutter.json` file for the starter
and not the `cookiecutter.json` for the pipeline template.
