# Hooks

## Introduction

Hooks are a mechanism to add extra behaviour to Kedro's main execution in an easy and consistent manner. Some examples may include:

* Adding a transformer after the data catalog is loaded
* Adding data validation to the inputs, before a node runs, and to the outputs, after a node has run. This makes it possible to integrate with other tools like [Great-Expectations](https://docs.greatexpectations.io/en/latest/)
* Adding machine learning metrics tracking, e.g. using [MLflow](https://mlflow.org/), throughout a pipeline run

## Concepts

A Hook is comprised of a Hook specification and Hook implementation. To add Hooks to your project you will need to:

* Provide a Hook implementation for an existing Hook specification defined by Kedro
* Register your Hook implementation in your `ProjectContext`


### Hook specification

Kedro defines Hook specifications for particular execution points where users can inject additional behaviour. Currently, the following Hook specifications are provided in [kedro.framework.hooks](/kedro.framework.hooks):

* `after_catalog_created`
* `before_node_run`
* `after_node_run`
* `on_node_error`
* `before_pipeline_run`
* `after_pipeline_run`
* `on_pipeline_error`


The naming convention for non-error Hooks is `<before/after>_<noun>_<past_participle>`, in which:

* `<before/after>` and `<past_participle>` refers to when the Hook executed, e.g. `before <something> was run` or `after <something> was created`.
* `<noun>` refers to the relevant component in the Kedro execution timeline for which this Hook adds extra behaviour, e.g. `catalog`, `node` and `pipeline`.

The naming convention for error hooks is `on_<noun>_error`, in which:

* `<noun>` refers to the relevant component in the Kedro execution timeline that throws the error.

[kedro.framework.hooks](/kedro.framework.hooks) lists the full specifications for which you can inject additional behaviours by providing an implementation.

### Hook implementation

You should provide an implementation for the specification that describes the point at which you want to inject additional behaviour.

A Hook implementation should have the same name as the specification. It provides a concrete implementation with a subset of the specification's parameters. For example, the full signature of the [`after_data_catalog_created`](/kedro.framework.hooks.specs.DataCatalogSpecs) Hook specification is:

```python
@hook_spec
def after_catalog_created(
    self,
    catalog: DataCatalog,
    conf_catalog: Dict[str, Any],
    conf_creds: Dict[str, Any],
    save_version: str,
    load_versions: Dict[str, str],
    run_id: str,
) -> None:
    pass
```

However, if you just want to use this Hook to add transformer for a data catalog after it is created, your Hook implementation can be as simple as:

```python
# <your_project>/src/<your_project>/hooks.py
from kedro.extras.transformers.time_profiler import ProfileTimeTransformer
from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog


class TransformerHooks:

    @hook_impl
    def after_catalog_created(self, catalog: DataCatalog) -> None:
        catalog.add_transformer(ProfileTimeTransformer())
```

> * To declare a Hook implementation, use the `@hook_impl` decorator
> * You only need to make use of a subset of arguments defined in the corresponding specification
> * Group related Hook implementations under a namespace, preferably a class
> * You can register more than one implementations for the same specification. They will be called in FIFO (first-in, first-out) order.


#### Registering your Hook implementations with Kedro

Hook implementations should be registered with Kedro through the `ProjectContext`:

```python
# <your_project>/src/<your_project>/run.py
from your_project.hooks import TransformerHooks


class ProjectContext(KedroContext):
    project_name = "kedro-tutorial"
    project_version = "0.16.1"

    hooks = (
        # register the collection of your Hook implementations here.
        # Note that we are using an instance here, not a class. It could also be a module.
        TransformerHooks(),
    )
    # You can add more than one hook by simply listing them
    # in a tuple.`hooks = (Hook1(), Hook2())`

    def _get_pipelines(self) -> Dict[str, Pipeline]:
        return create_pipelines()
```

This ensures that the `after_data_catalog_created` implementation above will be called automatically after every time a data catalog is created.

## Under the hood

Under the hood, we use [pytest's pluggy](https://pluggy.readthedocs.io/en/latest/) to implement Kedro's Hook mechanism. We recommend reading their documentation if you have more questions about the underlying implementation.
