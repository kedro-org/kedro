# Hooks

## Introduction

Hooks are a mechanism to add extra behaviours to Kedro's main execution in an easy and consistent manner. Some examples of these extra behaviours include:

* Adding a transformer after the data catalog is loaded;
* Adding data validation to the inputs, before a node runs, and to the outputs, after a node has run. This makes it possible to integrate with other tools like [Great-Expectations](https://docs.greatexpectations.io/en/latest/);
* Adding machine learning metrics tracking, e.g. using [MLflow](https://mlflow.org/), throughout a pipeline run.

## Concepts

The general process you should follow to add hooks to your project is:

* Provide a hook implementation for an existing hook specification defined by Kedro.
* Register this hook implementation in your `ProjectContext`.

To elaborate, first, let's look at the two sides that comprise a hook:

### Hook specification

A hook specification is defined by Kedro as a particular point in Kedro's execution where users can inject additional behaviours. Currently, the following hook specifications are provided by Kedro in [kedro.framework.hooks](/kedro.framework.hooks):

* `after_catalog_created`
* `before_node_run`
* `after_node_run`
* `on_node_error`
* `before_pipeline_run`
* `after_pipeline_run`
* `on_pipeline_error`

The naming convention for non-error hooks is `<before/after>_<noun>_<past_participle>`, in which:

* `<before/after>` and `<past_participle>` refers to when the hook executed, e.g. `before <something> was run` or `after <something> was created`.
* `<noun>` refers to the relevant component in the Kedro execution timeline for which this hook adds extra behaviour, e.g. `catalog`, `node` and `pipeline`.

The naming convention for error hooks is `on_<noun>_error`, in which:

* `<noun>` refers to the relevant component in the Kedro execution timeline that throws the error.

To view their full signatures, please visit [kedro.framework.hooks](/kedro.framework.hooks). As a user, you can inject additional behaviours by providing implementation for these specifications.

### Hook implementation

A hook implementation should have the same name as the specification and provide a concrete implementation with a subset of the specification's parameters. For example, the full signature of the [`after_data_catalog_created`](/kedro.framework.hooks.specs.DataCatalogSpecs) hook specification is:

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

However, if you just want to use this hook to add transformer for a data catalog after it is created, your hook implementation can be as simple as:

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

Here are some additional considerations that you should have:
* To declare a hook implementation, use the `@hook_impl` decorator.
* You only need to make use of a subset of arguments defined in the corresponding specification.
* Related hook implementations should be grouped under a namespace, preferably a class.
* You can register more than one implementations for the same specification. They will be called in FIFO (first-in, first-out) order.

### Registering your hook implementations with Kedro

Hook implementations should be registered with Kedro through the `ProjectContext`:

```python
# <your_project>/src/<your_project>/run.py
from your_project.hooks import TransformerHooks


class ProjectContext(KedroContext):
    project_name = "kedro-tutorial"
    project_version = "0.16.0"

    hooks = (
        # register the collection of your hook implementations here.
        # Note that we are using an instance here, not a class. It could also be a module.
        TransformerHooks(),
    )
    # You can add more than one hook by simply listing them
    # in a tuple.`hooks = (Hook1(), Hook2())`

    def _get_pipelines(self) -> Dict[str, Pipeline]:
        return create_pipelines()
```

And with this, your `after_data_catalog_created` implementation will be called automatically after every time a data catalog is created.

## Under the hood

Under the hood, we use [pytest's pluggy](https://pluggy.readthedocs.io/en/latest/) to implement this hook mechanism. We recommend reading their documentation if you have more questions about the underlying implementation.
