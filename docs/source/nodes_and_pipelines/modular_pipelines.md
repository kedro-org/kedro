# Modular pipelines

In many typical Kedro projects, a single (“main”) pipeline increases in complexity as the project evolves. To keep your project fit for purpose, we recommend you **separate your code into different pipelines (modules)** that are logically isolated and can be reused. Each pipeline should ideally be organised in its own folder, promoting easy copying and reuse within and between projects. Simply put: one pipeline, one folder.

Kedro supports this concept of modular pipelines with the following tools:
- [How to create a new blank pipeline using the `kedro pipeline create` command](#how-to-create-a-new-blank-pipeline-using-the-kedro-pipeline-create-command)
- [How to structure your pipeline creation](#how-to-structure-your-pipeline-creation)
- [How to use custom new pipeline templates](#how-to-use-custom-new-pipeline-templates)
- [How to share your pipelines](#how-to-share-your-pipelines)

## How to create a new blank pipeline using the `kedro pipeline create` command

 To create a new modular pipeline, use the following command:

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
    │       └── {{pipeline_name}}      <-- This folder defines the modular pipeline
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

If you want to delete an existing pipeline, you can use `kedro pipeline delete <pipeline_name>` to do so.
```{note}
To see the full list of available CLI options, you can run `kedro pipeline create --help`.
```

## How to structure your pipeline creation

After creating the pipeline with `kedro pipeline create`, you will find template code in `pipeline.py` that you need to fill with your actual pipeline code:

```python
# src/my_project/pipelines/{{pipeline_name}}/pipeline.py
from kedro.pipeline import Pipeline, pipeline

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([])
```
Here, you are creating a `create_pipeline()` function that returns a `Pipeline` class instance with the help of the `pipeline` function. You should keep the function name as `create_pipeline()` because this allows kedro to [automatically discover the pipeline](pipeline_registry.md#pipeline-autodiscovery). Otherwise, the pipeline would need to be [registered manually](pipeline_registry.md#the-pipeline-registry).

Before filling `pipeline.py` with nodes, we recommend storing all node functions in `nodes.py`. From our previous example, we should add the functions `mean()`, `mean_sos()` and `variance()` into `nodes.py`:

```python
# src/my_project/pipelines/{{pipeline_name}}/nodes.py
def mean(xs, n):
    return sum(xs) / n

def mean_sos(xs, n):
    return sum(x**2 for x in xs) / n

def variance(m, m2):
    return m2 - m * m
```

Then we can assemble a pipeline from those nodes as follows:

```python
# src/my_project/pipelines/{{pipeline_name}}/pipelines.py
from kedro.pipeline import Pipeline, pipeline, node

from .nodes import mean, mean_sos, variance
# Import node functions from nodes.py located in the same folder

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(len, "xs", "n"),
            node(mean, ["xs", "n"], "m", name="mean_node", tags="tag1"),
            node(mean_sos, ["xs", "n"], "m2", name="mean_sos", tags=["tag1", "tag2"]),
            node(variance, ["m", "m2"], "v", name="variance_node"),
        ],  # A list of nodes and pipelines combined into a new pipeline
        tags="tag3",  # Optional, each pipeline node will be tagged
        namespace="",  # Optional
        inputs={},  # Optional
        outputs={},  # Optional
        parameters={},  # Optional
    )
```
Here it was shown that pipeline creation function have few optional parameters, you can use:
- tags on a pipeline level to apply them for all nodes inside of pipeline
- namespace, inputs, outputs and parameters to reuse pipelines. More about that you can find at [Reuse pipelines with namespaces](namespaces.md)


## How to use custom new pipeline templates

If you want to generate a pipeline with a custom Cookiecutter template, you can save it in `<project_root>/templates/pipeline`.
The `kedro pipeline create` command will pick up the custom template in your project as the default. You can also specify the path to your custom
Cookiecutter pipeline template with the `--template` flag like this:
```bash
kedro pipeline create <pipeline_name> --template <path_to_template>
```
A template folder passed to `kedro pipeline create` using the `--template` argument will take precedence over any local templates.
Kedro supports having a single pipeline template in your project. If you need to have multiple pipeline templates, consider saving them in a
separate folder and pointing to them with the `--template` flag.

### Creating custom pipeline templates

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


## Providing pipeline specific dependencies

* A pipeline **might** have external dependencies specified in a local `requirements.txt` file.
* Pipeline specific dependencies are scooped up during the [micro-packaging](micro_packaging.md) process.
* These dependencies need to be manually installed using `pip`:
```bash
pip install -r requirements.txt
```


## How to share your pipelines

> **Warning:** Micro-packaging is deprecated and will be removed from Kedro version 0.20.0.

Pipelines are shareable between Kedro codebases via [micro-packaging](micro_packaging.md), but you must follow a couple of rules to ensure portability:

* A pipeline that you want to share needs to be separated in terms of its folder structure. `kedro pipeline create` command makes this easy.
* Pipelines should **not** depend on the main Python package, as this would break portability to another project.
* Catalog references are not packaged when sharing/consuming pipelines, i.e. the `catalog.yml` file is not packaged.
* Kedro will only look for top-level configuration in `conf/`; placing a configuration folder within the pipeline folder will have no effect.
* We recommend that you document the configuration required (parameters and catalog) in the local `README.md` file for any downstream consumers.
