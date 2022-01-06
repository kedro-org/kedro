# Modular pipelines

## What are modular pipelines?

In many typical Kedro projects, a single (“main”) pipeline increases in complexity as the project evolves. To keep your project fit for purpose, we recommend that you create modular pipelines, which are logically isolated and can be reused. Modular pipelines are easier to develop, test and maintain, and are portable so they can be copied and reused between projects.

Modular pipelines allow you to instantiate pipelines multiple times whilst allowing the user to override inputs/outputs/parameters. They are reusable within the same codebase and shareable across projects via [micro-packaging](04_micro_packaging.md). This is the modern way to use Kedro and will change the way you think about your pipelines.

```eval_rst
.. note:: The Kedro project visualised below is representative of one that might be seen in the real world. It takes full advantage of modular pipelines for ``Data Ingestion``, ``Feature Engineering``, ``Reporting`` and ``Train Evaluation`` (which even includes nested instances).
```

### Key concepts

In this section you will learn about how to take advantage of modular pipelines, the key points have been listed below:

1. **A modular pipeline is defined by its folder structure**

   * You can generate this file structure with the CLI command ``kedro pipeline create <pipeline_name>``.
   * The folder structure keeps things isolated and encourages portability.

2. **Modular pipelines are designed to be portable and reusable**

   * It's possible to re-use the same pipeline multiple times within the same project (with different inputs/outputs or parameters).
   * You can also share pipelines across codebases via [micro-packaging](04_micro_packaging.md).

3. **The `kedro.pipeline.modular_pipeline.pipeline` wrapper method unlocks the real power of modular pipelines**

   * Applying namespaces allows you to simplify your mental model and isolate 'within pipeline' processing steps.
   * ``Kedro-Viz`` is able to accelerate development by [rendering namespaced](../03_tutorial/06_visualise_pipeline.md) pipelines as collapsible 'super nodes'.

<iframe
    src="http://demo.kedro.org"
    width="850",
    height="600"
></iframe>

## How do I create a modular pipeline?

You can use a [project-specific CLI command](../09_development/03_commands_reference.md#kedro-commands) to create a modular pipeline. The pipeline name must adhere to [Python convention](https://realpython.com/python-pep8/#naming-conventions).

```bash
kedro pipeline create <pipeline_name>
```

```eval_rst
.. note:: For the full list of available CLI options, you can always run ``kedro pipeline create --help`` for more information.
```

### What does the ``kedro pipeline create`` do?

Running the `pipeline create` command adds the following folder structure to your project. For your convenience Kedro gives you a pipeline-specific `nodes.py`, `pipeline.py`, parameters and appropriate `tests` structure. You also don't have to add those pesky `__init__.py` files yourself, which is handy 😅.

<details>
<summary><b>Click to see the generated folder structure</b></summary>

```text
├── conf
│   └── base
│       └── parameters
│           └── {{pipeline_name}}.yml  <-- Pipeline specific parameters
└── src
    ├── my_project
    │   ├── __init__.py
    │   ├── pipelines
    │   |   ├── __init__.py
    │   |   └── {{pipeline_name}}      <-- This folder defines the modular pipeline
    │   |       ├── README.md          <-- To store pipeline specific documentation 
    │   |       ├── __init__.py        <-- So that Python treats this pipeline as a module
    │   |       ├── nodes.py           <-- To declare your nodes
    │   |       └── pipeline.py        <-- To structure the pipeline itself
    |   └──  pipeline_registry.py      <-- Does NOT automatically update the registry 
    └── tests
        ├── __init__.py
        └── pipelines
            ├── __init__.py
            └── {{pipeline_name}}      <-- Pipeline specific tests
                ├── __init__.py
                └── test_pipeline.py

```

</details>

If you want to do the reverse and remove a modular pipeline, you can use ``kedro pipeline delete`` to do so.

### Ensuring portability

Kedro modular pipelines are shareable between Kedro codebases via [micro-packaging](04_micro_packaging.md), but you need to follow a couple of rules to ensure portability:

* Modular pipelines should **not** depend on the main Python package as this would break portability to another project.
* Catalog references are not packaged when sharing/consuming modular pipelines.
* Kedro will only look for top level configuration `/conf/`, therefore providing a configuration folder within the pipeline folder will have no effect.
* It is recommended that you document the configuration required (parameters and catalog) in the local `README.md` file for any downstream consumers.

### Providing modular pipeline specific dependencies

* A modular pipeline **may** have external dependencies specified in a local `requirements.txt` file.
* Pipeline specific dependencies are scooped up during the [micro-packaging](04_micro_packaging.md) process.
* These dependencies are _not_ currently installed by the [`kedro install`](../09_development/03_commands_reference.md#install-all-package-dependencies) command and will have to be manually installed.

## Using the modular `pipeline()` wrapper to provide overrides

This wrapper really unlocks the power of modular pipelines.

* It allows you to start instantiating the same pipeline multiple times.
* These will be static in terms of structure, but dynamic in terms of `inputs`/`outputs`/`parameters`.
* It also allows you to simplify both your mental models and Kedro-Viz visualisations via `namespaces`.

```python
from kedro.pipeline.modular_pipeline import pipeline
```

The `pipeline()` wrapper method takes the following arguments:

```eval_rst
+--------------------+---------------------------------------------------------------------+
| Keyword argument   | Description                                                         |
+====================+=====================================================================+
| ``pipe``           | The `Pipeline` object you want to wrap                              |
+--------------------+---------------------------------------------------------------------+
| ``inputs``         | Any overrides provided to this instance                             |
+--------------------+ of the underlying wrapped ``Pipeline`` object                       |
| ``outputs``        |                                                                     |
+--------------------+                                                                     |
| ``parameters``     |                                                                     |
+--------------------+---------------------------------------------------------------------+
| ``namespace``      | The namespace that will be encapsulated by this pipeline instance   |
+--------------------+---------------------------------------------------------------------+
```

## Combining disconnected pipelines

Sometimes two pipelines need to be connected, but do not share any catalog dependencies. The wrapper can be used to solve that.

<details>
<summary>Click here to see a worked example</summary>

```python
cook_pipeline = Pipeline(
    [
        node(
            func=defrost, 
            inputs="frozen_veg", 
            outputs="veg"
        ), 
        node(
            func=grill, 
            inputs="veg", 
            outputs="grilled_veg"
        )
    ]
)

lunch_pipeline = Pipeline(
    [
        node(
            func=eat, 
            inputs="food", 
            outputs=None
        )
    ]
)

cook_pipeline + lunch_pipeline 
```

This combination will visualise since it's valid pre-runtime, but it will not run since `food` is not an output of the cook pipeline:

![disjoined](../meta/images/cook_disjointed.png)

* Combining `cook_pipeline + lunch_pipeline` will not work since `food` doesn't exist as an output of the `cook_pipeline`.
* In this case, we will need to map `grilled_veg` to the expected input of `food`.

The wrapper allows us to provide a mapping and fix this disconnect.

```python
from kedro.pipeline.modular_pipeline import pipeline

prep_pipeline = pipeline(
        pipe=cook_pipeline, 
        inputs={"food" : "grilled_veg"} 
)

meal_pipeline = prep_pipeline + lunch_pipeline
```

Providing this input/output override will join up the pipeline nicely:

![joined](../meta/images/cook_joined.png)

```eval_rst
.. note:: In this example we have used the ``+`` operator to join two pipelines. Remember you can also use ``sum()`` or pass a list of pipelines to the ``Pipeline()`` constructor as well.
```

</details>

## Using a modular pipeline multiple times

Reusing pipelines for slightly different purposes can be a real accelerator for teams and organisations when they reach a certain scale.

* Namespaces allow you to '[instantiate](https://en.wikipedia.org/wiki/Instance_(computer_science))' the same pipeline multiple times and keep operations isolated.
* Like one provides arguments to a class' constructor, you can provide overriding inputs/outputs/parameters to the `pipeline()` wrapper

<details>
<summary>Click here to see a worked example</summary>

```python
cook_pipeline = Pipeline(
    [
        node(
            func=defrost, 
            inputs="frozen_veg", 
            outputs="veg", 
            name="defrost_node"
        ),
        node(
            func=grill, 
            inputs="veg", 
            outputs="grilled_veg"
        ),
    ]
)

eat_breakfast_pipeline = Pipeline(
    [
        node(
            func=eat_breakfast, 
            inputs="breakfast_food", 
            outputs=None
        )
    ]
)
eat_lunch_pipeline = Pipeline(
    [
        node(
            func=eat_lunch, 
            inputs="lunch_food", 
            outputs=None
        )
    ]
)

cook_pipeline + eat_breakfast_pipeline + eat_lunch_pipeline 
```

If we visualise the snippet above, we see a disjointed pipeline:

* We need to "defrost" two different types of food via different pipelines.
* We can't use the `cook_pipeline` twice because the internal dataset names will conflict.
* Mapping all datasets via the `pipeline()`  wrapper will also cause conflicts.

![cook no namespace](../meta/images/cook_no_namespace.png)

Adding namespaces solves this issue:

```python
cook_breakfast_pipeline = pipeline(
    pipe=cook_pipeline,
    inputs="frozen_veg",  # inputs stay the same, don't namespace
    outputs={"grilled_veg": "breakfast_food"},
    namespace="breakfast",
)
cook_lunch_pipeline = pipeline(
    pipe=cook_pipeline,
    inputs="frozen_veg",  # inputs stay the same, don't namespace
    outputs={"grilled_veg": "lunch_food"},
    namespace="lunch",
)

final_pipeline = (
    cook_breakfast_pipeline
    + eat_breakfast_pipeline
    + cook_lunch_pipeline
    + eat_lunch_pipeline
)
```

* `namespace="lunch"` renames all datasets and nodes, prefixing them with `"lunch."`.
* The datasets that we explicitly "freeze" (`frozen_veg`) or remap (`grilled_veg`) are not affected/prefixed.
* Remapping free outputs is required since "breakfast_food" and "lunch_food" are the names expected by the `eat_breakfast_pipeline` and `eat_lunch_pipeline` respectively.
* The resulting pipeline now has two separate nodes, `breakfast.defrost_node` and `lunch.defrost_node`.
* Also two separate datasets `breakfast.veg` and `lunch.veg` connect the nodes inside the pipelines, causing no confusion between them.

![namespaced](../meta/images/cook_namespaced.gif)

* Visualising the `final_pipeline` highlights how namespaces become 'super nodes' which encapsulate the wrapped pipeline.
* This example demonstrates how we can reuse the same `cook_pipeline` with slightly different arguments.
* In the real world, one could imagine pipelines with responsibilities like profiling or feature engineering being reused within the same project or even across projects via [micro-packaging](04_micro_packaging.md).
* Namespaces can also be arbitrarily nested with the `.` character.

```eval_rst
.. note:: Parameter references (``params:`` and ``parameters``) will not be namespaced
```

</details>

## How to use a modular pipeline with different parameters

 Mapping parameter values is very similar to the way we map inputs and outputs.

<details>
<summary>Click here to see a worked example</summary>

* We instantiate the `template_pipeline` twice, but pass in different parameters.
* `input1` and `input2` are 'frozen' and thus shared in both instances.
* `params:override_me` does not actually exist and is designed to be overridden in both cases.
* Providing a namespace isolates the intermediate operation and visualises nicely.

```python
template_pipeline = Pipeline(
    [
        node(
            func=node_func1, 
            inputs=["input1", "input2", "params:override_me"], 
            outputs="intermediary_output"
        ),
        node(
            func=node_func2, 
            inputs="intermediary_output", 
            outputs="output"
        ),
    ]
)

alpha_pipeline = pipeline(
    pipe=template_pipeline,
    inputs={"input1", "input2"},
    parameters={"params:override_me": "params:alpha"}
    namespace="alpha"
)

beta_pipeline = pipeline(
    pipe=template_pipeline,
    inputs={"input1", "input2"},
    parameters={"params:override_me": "params:beta"},
    namespace="beta",
)

final_pipeline = alpha_pipeline + beta_pipeline
```

</details>

![namespaced_params](../meta/images/cook_params.png)
