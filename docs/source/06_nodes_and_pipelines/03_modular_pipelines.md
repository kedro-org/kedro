# Modular pipelines

> *Note:* This documentation is based on `Kedro 0.17.1`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

## What are modular pipelines?

In many typical Kedro projects, a single (“main”) pipeline increases in complexity as the project evolves. To keep your project fit for purpose, we recommend that you create modular pipelines, which are logically isolated and can be reused. Modular pipelines are easier to develop, test and maintain, and are portable so they can be copied and reused between projects.

## How do I create a modular pipeline?

You can use a [project-specific CLI command](../09_development/03_commands_reference.md#kedro-commands) to create a modular pipeline. The pipeline name must adhere to [generic Python module naming rules](https://realpython.com/python-pep8/#naming-conventions):

* Can only contain alphanumeric characters and underscores (`A-Za-z0-9_`)
* Must start with a letter or underscore
* Must be at least 2 characters long

> *Note:* Since `kedro pipeline` is a group of project-specific commands, those will only show up when your current working directory is the project root. If you see an error message like `Error: No such command 'pipeline'`, this indicates that your working directory does not point to a valid Kedro project.

For the full list of available CLI options, you can always run `kedro pipeline create --help` for more information.

```bash
kedro pipeline create <pipeline_name>
```

> *Note:* Although Kedro does not enforce the following project structure, we strongly encourage that you use it when you develop your modular pipelines. Future versions of Kedro may assume this structure.

The `kedro pipeline create <pipeline_name>` command creates the following:

***A modular pipeline in a subfolder***

The command creates a modular pipeline in `src/<python_package>/pipelines/<pipeline_name>/`. The folder contains the following files:

* `__init__.py` to make Python treat the code in the subfolder as a module
* boilerplate `README.md` for you to record information regarding the pipeline's execution
* `nodes.py` as a location for you to add code for the nodes in your new modular pipeline
* `pipeline.py` to expose the `create_pipeline` function at the top-level of the module. Calling `create_pipeline` with no arguments should return an instance of a [Pipeline](/kedro.pipeline.Pipeline):

```python
from <project-name>.pipelines import my_modular_pipeline_1

pipeline = my_modular_pipeline_1.create_pipeline()
```

> Note: When you run `kedro pipeline create` it does _not_ automatically add a corresponding entry to `register_pipelines()` in `src/<python_package>/pipeline_registry.py`.
> In order to make your new pipeline runnable (using the `kedro run --pipeline <pipeline_name>` CLI command, for example), you need to modify `src/<python_package>/pipeline_registry.py` yourself.

***Boilerplate configuration files***

The `kedro pipeline create <pipeline_name>` command also creates a boilerplate parameter configuration file, `<pipeline_name>.yml`, in `conf/<env>/parameters/`, where `<env>` defaults to `base`.

> *Note:* project configuration from `conf/base/parameters/<pipeline_name>.yml` is automatically discoverable by [KedroContext](/kedro.framework.context.KedroContext) and requires no manual change.

***A placeholder folder for unit tests***

Finally, `kedro pipeline create <pipeline_name>` also creates a placeholder for the pipeline unit tests in `src/tests/pipelines/<pipeline_name>/`.

## Recommendations
For ease of use and portability, consider these recommendations as you develop a modular pipeline:

* A modular pipeline should include a `README.md`, with all the information regarding its execution
* A modular pipeline _may_ have external dependencies specified in `requirements.txt`. These dependencies are _not_
 currently installed by the [`kedro install`](../09_development/03_commands_reference.md#install-all-package-dependencies) command, so users of your pipeline would have to run `pip install -r src/<python_package>/pipelines/<pipeline_name>/requirements.txt` before using the pipeline
* To ensure portability, modular pipelines should use relative imports when accessing their own objects and absolute imports otherwise. For example, in `pipeline.py`:

```python
from external_package import add  # importing from external package
from kedro.pipeline import node, Pipeline

from .nodes import node1_func, node2_func  # importing its own node functions


def create_pipeline():
    node1 = node(func=node1_func, inputs="a", outputs="b")
    node2 = node(func=node2_func, inputs="c", outputs="d")
    node3 = node(func=add, inputs=["b", "d"], outputs="sum")
    return Pipeline([node1, node2, node3])
```

* Modular pipelines should _not_ depend on the main Python package (`new_kedro_project` in this example) as this would break portability to another project
* Modular pipelines should be registered and stitched together in a main (or `__default__`) pipeline located in `src/new_kedro_project/pipeline_registry.py`

The following example, illustrates how to import and instantiate two modular pipelines (`modular_pipeline_1` and `modular_pipeline_2`) within `src/new_kedro_project/pipeline_registry.py`:

```python
from typing import Dict

from kedro.pipeline import Pipeline

from new_kedro_project.pipelines import (
    modular_pipeline_1 as mp1,
    modular_pipeline_2 as mp2,
)


def register_pipelines() -> Dict[str, Pipeline]:
    pipeline1 = mp1.create_pipeline()
    pipeline2 = mp2.create_pipeline()
    pipeline_all = pipeline1 + pipeline2
    return {"mp1": pipeline1, "mp2": pipeline2, "__default__": pipeline_all}
```

To run a pipeline by name from the command line:

```bash
kedro run --pipeline mp2
```

## How to share a modular pipeline

### Package a modular pipeline
Since Kedro 0.16.4 you can package a modular pipeline by executing `kedro pipeline package <pipeline_name>` command, which will generate a new [wheel file](https://pythonwheels.com/) for it. By default, the wheel file will be saved into `src/dist` directory inside your project, however this can be changed using the `--destination` (`-d`) option.

When you package your modular pipeline, Kedro will also automatically package files from 3 locations:

*  All the modular pipeline code in `src/<python_package>/pipelines/<pipeline_name>/`
*  Parameter files that match the glob pattern `conf/<env>/parameters*/**/*<pipeline_name>*`, where `<env>` defaults to `base`. If you need to capture the parameters from a different config environment, run `kedro pipeline package --env <env_name> <pipeline_name>`
*  Pipeline unit tests in `src/tests/pipelines/<pipeline_name>`

> _Note:_ Kedro _will not_ package the catalog config files even if those are present in `conf/<env>/catalog/<pipeline_name>.yml`.

If you plan to publish your packaged modular pipeline to some Python package repository like [PyPI](https://pypi.org/), you need to make sure that your modular pipeline name doesn't clash with any of the existing packages in that repository. However, there is no need to rename any of your source files if that is the case. Simply alias your package with a new name by running `kedro pipeline package --alias <new_package_name> <pipeline_name>`.

In addition to [PyPI](https://pypi.org/), you can also share the packaged wheel file directly, or via a cloud storage such as AWS S3.

### Pull a modular pipeline

You can pull a modular pipeline from a wheel file by executing `kedro pipeline pull <package_name>`, where `<package_name>` is either a package name on PyPI or a path to the wheel file. Kedro will unpack the wheel file, and install the files in following locations in your Kedro project:

*  All the modular pipeline code in `src/<python_package>/pipelines/<pipeline_name>/`
*  Configuration files in `conf/<env>/parameters/<pipeline_name>.yml`, where `<env>` defaults to `base`. If you want to place the parameters from a different config environment, run `kedro pipeline pull <pipeline_name> --env <env_name>`
*  Pipeline unit tests in `src/tests/pipelines/<pipeline_name>`

You can pull a modular pipeline from different locations, including local storage, PyPI and the cloud:

- Pulling a modular pipeline from a local directory:

```bash
kedro pipeline pull <path-to-your-project-root>/src/dist/<pipeline_name>-0.1-py3-none-any.whl
```

- Pulling a modular pipeline from S3:

```bash
kedro pipeline pull https://<bucket_name>.s3.<aws-region>.amazonaws.com/<pipeline_name>-0.1-py3-none-any.whl
```

- Pulling a modular pipeline from PyPI:

```bash
kedro pipeline pull <pypi-package-name>
```

If you are pulling the pipeline from a location that isn't PyPI, Kedro uses [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to locate and pull down your pipeline. If you need to provide any `fsspec`-specific arguments (say, if you're pulling your pipeline down from an S3 bucket and want to provide the S3 credentials inline or from a local server that requires tokens in the header) then you can use the `--fs-args` option to point to a YAML (or any `anyconfig`-supported configuration) file that contains the required configuration.

```bash
kedro pipeline pull https://<url-to-pipeline.whl> --fs-args pipeline_pull_args.yml
```

where

```
# pipeline_pull_args.yml
client_kwargs:
  headers:
    Authorization: token <token>
```

## A modular pipeline example template

Here is an example of a modular pipeline which combines all of these concepts within a Kedro project:

* The modular pipelines:
  - `src/new_kedro_project/pipelines/data_engineering` - A pipeline that imputes missing data and discovers outlier data points
  - `src/new_kedro_project/pipelines/feature_engineering` - A pipeline that generates temporal features while aggregating data and performs a train/test split on the data
  - `src/new_kedro_project/pipelines/modelling` - A pipeline that fits models, does hyperparameter search and reports on model performance
* A main (or `__default__`) pipeline:
  - `src/new_kedro_project/pipeline_registry.py` - combines 3 modular pipelines from the above

<details>
<summary><b>Click to expand</b></summary>

```console
new-kedro-project
├── .ipython/
├── conf/
├── data/
├── docs/
├── logs/
├── notebooks/
├── src
│   ├── new_kedro_project
│   │   ├── pipelines
│   │   │   ├── data_engineering
│   │   │   │   ├── __init__.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── README.md
│   │   │   ├── feature_engineering
│   │   │   │   ├── __init__.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── README.md
│   │   │   ├── modelling
│   │   │   │   ├── __init__.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── README.md
│   │   │   └── __init__.py
│   │   ├── __init__.py
|   |   ├── cli.py
│   │   ├── hooks.py
│   │   ├── pipeline_registry.py
│   │   ├── __main__.py
|   |   └── settings.py
│   ├── tests
│   │   ├── __init__.py
│   │   ├── pipelines
│   │   │   ├── data_engineering
│   │   │   │   ├── __init__.py
│   │   │   │   └── test_pipeline.py
│   │   │   ├── feature_engineering
│   │   │   │   ├── __init__.py
│   │   │   │   └── test_pipeline.py
│   │   │   ├── modelling
│   │   │   │   ├── __init__.py
│   │   │   │   └── test_pipeline.py
│   │   └── test_run.py
│   ├── requirements.txt
│   └── setup.py
├── pyproject.toml
├── README.md
└── setup.cfg
```
</details>

### Configuration

Nested configuration in modular pipelines is _not_ supported by Kedro. It means that putting config files (like `catalog.yml`) in `src/<python_package>/pipelines/<pipeline_name>/conf` will have no effect on the Kedro project configuration, however you may document it as a custom step that other users must complete as part of setting up your modular pipeline.

If you plan to manually hand off your modular pipeline to another project, you should document the configuration used by the pipeline in the `README.md` of your modular pipeline. For example, you may copy your configuration into the modular pipeline location before the pipeline hand off and instruct the users to copy `catalog.yml` into their top-level configuration:

```bash
mkdir conf/base/catalog/  # create a separate folder for the pipeline configs
cp src/<python_package>/pipelines/data_engineering/conf/catalog.yml conf/base/catalog/data_engineering.yml  # copy the pipeline configs
```

### Datasets

It is important to keep in mind that Kedro resolves the execution order of your pipeline's node based on their input and output datasets.

For example, if `node1` outputs the dataset `A`, and `node2` requires the dataset `A` as an input, then `node1` is guaranteed to be executed before `node2` when Kedro runs the pipeline.

As a modular pipeline developer, you may not know how your pipeline will be integrated in the downstream projects and what data catalog configuration they may have. Therefore, it is crucial to make it clear in the pipeline documentation what datasets (names and types) are required as inputs by your modular pipeline and what datasets it produces as outputs.

## How to connect existing pipelines

When two existing pipelines need to work together, they should be connected by the input and output datasets. But the names might be different, requiring manual fixes to be applied to the pipeline itself. An alternative solution would be to use `pipeline()`, the modular pipelines connector.

You can think of `pipeline()` as an equivalent to `node()`, which accepts an underlying function, inputs and outputs, and returns a `Node` object. Similarly, `pipeline()` accepts the underlying pipeline, inputs and outputs, and returns a `Pipeline` object.

Consider this example:

```python
cook_pipeline = Pipeline(
    [node(defrost, "frozen_meat", "meat"), node(grill, "meat", "grilled_meat"),]
)

lunch_pipeline = Pipeline([node(eat, "food", None),])
```

A simple `cook_pipeline + lunch_pipeline` doesn't work, because the `grilled_meat` output in the `cook_pipeline` needs to be mapped to the `food` input in the `lunch_pipeline`. This can be done in any of the following three (equivalent) ways:

```python
from kedro.pipeline import pipeline

final_pipeline1 = (
    pipeline(cook_pipeline, outputs={"grilled_meat": "food"}) + lunch_pipeline
)

# or
final_pipeline2 = cook_pipeline + pipeline(
    lunch_pipeline, inputs={"food": "grilled_meat"}
)

# or
final_pipeline3 = pipeline(
    cook_pipeline, outputs={"grilled_meat": "new_name"}
) + pipeline(lunch_pipeline, inputs={"food": "new_name"})
```

Remember you can pass `Pipeline` objects in the constructor as well, like in the example below. This approach is cleaner and more idiomatic when you are combining multiple modular pipelines together.

```python
final_pipeline = Pipeline(
    [
        pipeline(cook_pipeline, outputs={"grilled_meat": "new_name"}),
        pipeline(lunch_pipeline, inputs={"food": "new_name"}),
        node(...),
        ...,
    ]
)
```

>*Note:* `inputs` should correspond to the pipeline free inputs, while `outputs` are either free or intermediary outputs.

## How to use a modular pipeline twice
Consider the example:

```python
cook_pipeline = Pipeline(
    [
        node(defrost, "frozen_meat", "meat", name="defrost_node"),
        node(grill, "meat", "grilled_meat"),
    ]
)

eat_breakfast_pipeline = Pipeline([node(eat_breakfast, "breakfast_food", None)])
eat_lunch_pipeline = Pipeline([node(eat_lunch, "lunch_food", None)])
```

Now we need to "defrost" two different types of food and input to different pipelines. But we can't use the `cook_pipeline` twice because the internal dataset names will conflict. We might try to call `pipeline()` and map all datasets, but the conflict from the explicitly set `name="defrost_node"` remains.

Here is a solution that uses a namespace:

```python
cook_breakfast_pipeline = pipeline(
    cook_pipeline,
    inputs="frozen_meat",  # inputs stay the same, don't namespace
    outputs={"grilled_meat": "breakfast_food"},
    namespace="breakfast",
)
cook_lunch_pipeline = pipeline(
    cook_pipeline,
    inputs="frozen_meat",  # inputs stay the same, don't namespace
    outputs={"grilled_meat": "lunch_food"},
    namespace="lunch",
)

final_pipeline = (
    cook_breakfast_pipeline
    + eat_breakfast_pipeline
    + cook_lunch_pipeline
    + eat_lunch_pipeline
)
```

`namespace="lunch"` renames all datasets and nodes, prefixing them with `"lunch."`, except those datasets that we explicitly "freeze" (`frozen_meat`) or remap (`grilled_meat`).

Remapping free outputs is required since "breakfast_food" and "lunch_food" are the names expected by the `eat_breakfast_pipeline` and `eat_lunch_pipeline` respectively.

The resulting pipeline now has two separate nodes, `breakfast.defrost_node` and `lunch.defrost_node`. Also two separate datasets `breakfast.meat` and `lunch.meat` connect the nodes inside the pipelines, causing no confusion between them.

Note that `pipeline()` will skip prefixing when node inputs contain parameter references (`params:` and `parameters`).

For example:

```python
raw_pipeline = Pipeline([node(node_func, ["input", "params:x"], "output")])
final_pipeline = pipeline(raw_pipeline, namespace="new")
# `final_pipeline` will be `Pipeline([node(node_func, ["new.input", "params:x"], "new.output")])`
```

## How to use a modular pipeline with different parameters

You can map parameter values in a similar way to inputs and outputs. Let's say you have two almost identical pipelines that differ by one parameter. You want to run the pipelines on the same set of inputs.

```python
alpha_pipeline = Pipeline(
    [
        node(node_func1, ["input1", "input2", "params:alpha"], "intermediary_output"),
        node(node_func2, "intermediary_output", "output"),
    ]
)
beta_pipeline = pipeline(
    alpha_pipeline,
    inputs={"input1", "input2"},
    parameters={"params:alpha": "params:beta"},
    namespace="beta",
)

final_pipeline = alpha_pipeline + beta_pipeline
```

The value of parameter `alpha` is replaced with the value of parameter `beta`, assuming they both live in your parameters configuration (`parameters.yml`). The namespace ensures that outputs are not overwritten, so intermediate and final outputs are prefixed, i.e. `beta.intermediary_output`, `beta.output`.

## How to clean up a modular pipeline
You can manually delete all the files that belong to a modular pipeline. However, Kedro also provides a CLI command to clean up automatically. It deletes the following files when you call `kedro pipeline delete <pipeline_name>`:



* All the modular pipeline code in `src/<python_package>/pipelines/<pipeline_name>/`
* Configuration files `conf/<env>/parameters/<pipeline_name>.yml` and `conf/<env>/catalog/<pipeline_name>.yml`, where `<env>` defaults to `base`. If the files are located in a different config environment, run `kedro pipeline delete <pipeline_name> --env <env_name>`.
* Pipeline unit tests in `tests/pipelines/<pipeline_name>/`

>*Note*: `kedro pipeline delete` won't remove the entry from `pipeline_registry.py` if you have imported the modular pipeline there.You must remove it manually to clean up, otherwise it will break your project because the import will raise an error.
