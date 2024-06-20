# Reuse pipelines with namespaces

In many typical Kedro projects, a single (“main”) pipeline increases in complexity as the project evolves. To keep your project fit for purpose, we recommend you separate your code into different pipelines (modules) that are logically isolated and can be reused.

## How to reuse your pipelines

If you want to create a new pipeline that performs the same tasks as your existing pipeline (e.g., `data_science`), you can use the same `pipeline()` creation function as described in [How to structure your pipeline creation](pipeline_introduction.md#how-to-structure-your-pipeline-creation). This function allows you to overwrite inputs, outputs, and parameters. Your new pipeline creation code should look like this:

```python
def create_new_pipeline(**kwargs) -> Pipeline:
    return pipeline(
    [data_science], # Name of an existing pipeline
    inputs = {"old_input_df_name" : "new_input_df_name"},
    outputs = {"old_output_df_name" : "new_output_df_name"},
    parameters = {"params: test_size1": "params: test_size2"},
    )
```
This means you can easily create multiple pipelines based on the `data_science` pipeline to test different approaches with various input datasets and model training parameters.

## What is a Namespace

If you need to try different options for training your model, constantly overwriting your outputs for each new pipeline can become tedious. Each model's results (outputs) should be saved in new objects, which can be annoying to manage manually. Namespaces are a perfect solution for this. By setting a `namespace="namespace_name"` parameter for each new pipeline (based on an existing pipeline), you achieve automatic output and node isolation. This is done by adding a `namespace_name` prefix to each pipeline node and output dataset. Your pipeline creation code will look like this:

```python
def create_new_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [data_science],  # Name of the existing pipeline
        inputs={"old_input_df_name": "new_input_df_name"},  # Mapping old input to new input
        parameters={"params:test_size1": "params:test_size2"},  # Updating parameters
        namespace="alternative_approach",  # Setting the namespace name
    )
```
In this example:
* The `data_science` pipeline is reused and namespaced under `alternative_approach`.
* The inputs and parameters are mapped to new names/values.
* The namespace parameter ensures that all nodes and outputs in this pipeline are prefixed with `alternative_approach`, isolating them from other pipelines.

Namespace methods:
* You can use `kedro run --namespace = namespace_name` to run only the specific namespace
* [Kedro-Viz](https://demo.kedro.org) accelerates development by rendering namespaced pipelines as collapsible 'super nodes'.

## How to share your pipelines

Pipelines are shareable between Kedro codebases via [micro-packaging](micro_packaging.md), but you must follow a couple of rules to ensure portability:

* A pipeline that you want to share needs to be separated in terms of its folder structure. `kedro pipeline create` command makes this easy.
* Pipelines should **not** depend on the main Python package, as this would break portability to another project.
* Catalog references are not packaged when sharing/consuming pipelines, i.e. the `catalog.yml` file is not packaged.
* Kedro will only look for top-level configuration in `conf/`; placing a configuration folder within the pipeline folder will have no effect.
* We recommend that you document the configuration required (parameters and catalog) in the local `README.md` file for any downstream consumers.

## Providing pipeline specific dependencies

* A pipeline **might** have external dependencies specified in a local `requirements.txt` file.
* Pipeline specific dependencies are scooped up during the [micro-packaging](micro_packaging.md) process.
* These dependencies need to be manually installed using `pip`:
```bash
pip install -r requirements.txt
```

## Example: Combining disconnected pipelines

Sometimes two pipelines must be connected, but do not share any catalog dependencies. In this example, there is a `lunch_pipeline`, which makes us lunch. The 'verbs', `defrost` and `eat`, are Python functions and the inputs/outputs are food at different points of the process (`frozen`, `thawed` and `food`).

```python
cook_pipeline = pipeline(
    [
        node(func=defrost, inputs="frozen_veg", outputs="veg"),
        node(func=grill, inputs="veg", outputs="grilled_veg"),
    ]
)

lunch_pipeline = pipeline([node(func=eat, inputs="food", outputs=None)])

cook_pipeline + lunch_pipeline
```

This combination will visualise since it's valid pre-runtime, but it will not run since `food` is not an output of the `cook_pipeline` because the output of the `cook_pipeline` is `grilled_veg`:

![disjoined](../meta/images/cook_disjointed.png)

* Combining `cook_pipeline + lunch_pipeline` will not work since `food` doesn't exist as an output of the `cook_pipeline`.
* In this case, we will need to map `grilled_veg` to the expected input of `food`.

The wrapper allows us to provide a mapping and fix this disconnect.

```python
from kedro.pipeline.modular_pipeline import pipeline

prep_pipeline = pipeline(pipe=cook_pipeline, outputs={"grilled_veg": "food"})

meal_pipeline = prep_pipeline + lunch_pipeline
```

Providing this input/output override will join up the pipeline nicely:

![joined](../meta/images/cook_joined.png)

```{note}
In this example we have used the `+` operator to join two pipelines. You can also use `sum()` or pass a list of pipelines to the `pipe` argument.
```


## Example: Using a modular pipeline multiple times

Reusing pipelines for slightly different purposes can be a real accelerator for teams and organisations when they reach a certain scale. In the real world, one could imagine pipelines with responsibilities like profiling or feature engineering being reused within the same project or even across projects via [micro-packaging](micro_packaging.md).

* In an ideal world, we would like to use the `cook_pipeline` twice as you would `defrost` and `grill` multiple meals beyond the `veg` currently hard-coded.
* Namespaces allow you to instantiate the same pipeline multiple times and keep operations isolated.
* Like one provides arguments to a class' constructor, you can provide overriding inputs/outputs/parameters to the `pipeline()` wrapper.

```{note}
The set of overriding inputs and outputs must be a subset of the reused pipeline's "free" inputs and outputs, respectively. A free input is an input that isn't generated by a node in the pipeline, while a free output is an output that isn't consumed by a node in the pipeline. {py:meth}`Pipeline.inputs() <kedro.pipeline.Pipeline.inputs>` and {py:meth}`Pipeline.outputs() <kedro.pipeline.Pipeline.outputs>` can be used to list a pipeline's free inputs and outputs, respectively.
```

```python
cook_pipeline = pipeline(
    [
        node(func=defrost, inputs="frozen_veg", outputs="veg", name="defrost_node"),
        node(func=grill, inputs="veg", outputs="grilled_veg"),
    ]
)

eat_breakfast_pipeline = pipeline(
    [node(func=eat_breakfast, inputs="breakfast_food", outputs=None)]
)
eat_lunch_pipeline = pipeline([node(func=eat_lunch, inputs="lunch_food", outputs=None)])

cook_pipeline + eat_breakfast_pipeline + eat_lunch_pipeline
```

If we visualise the snippet above, we see a disjointed pipeline:

* We need to "defrost" two different types of food via different pipelines.
* We cannot use the `cook_pipeline` twice because the internal dataset names will conflict.
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
* Namespaces can also be arbitrarily nested with the `.` character.
* `kedro run --namespace=<namespace>` could be used to only run nodes with a specific namespace.

```{note}
`parameters` references will not be namespaced, but `params:` references will.
```

## Example: How to reuse a pipeline with different parameters

 Mapping parameter values is very similar to the way we map inputs and outputs.

* We instantiate the `template_pipeline` twice, but pass in different parameters.
* `input1` and `input2` are 'frozen' and thus shared in both instances.
* `params:override_me` does not actually exist and is designed to be overridden in both cases.
* Providing a namespace isolates the intermediate operation and visualises nicely.

```python
template_pipeline = pipeline(
    [
        node(
            func=node_func1,
            inputs=["input1", "input2", "params:override_me"],
            outputs="intermediary_output",
        ),
        node(
            func=node_func2,
            inputs="intermediary_output",
            outputs="output",
        ),
    ]
)

alpha_pipeline = pipeline(
    pipe=template_pipeline,
    inputs={"input1", "input2"},
    parameters={"params:override_me": "params:alpha"},
    namespace="alpha",
)

beta_pipeline = pipeline(
    pipe=template_pipeline,
    inputs={"input1", "input2"},
    parameters={"params:override_me": "params:beta"},
    namespace="beta",
)

final_pipeline = alpha_pipeline + beta_pipeline
```

![namespaced_params](../meta/images/cook_params.png)
