# The pipeline registry

Projects generated using Kedro 0.17.2 or later define their pipelines in `src/<package_name>/pipeline_registry.py`. This, in turn, populates the `pipelines` variable in [`kedro.framework.project`](/kedro.framework.project) that the Kedro CLI and plugins use to access project pipelines. The `pipeline_registry` module must contain a top-level `register_pipelines()` function that returns a mapping from pipeline names to [`Pipeline`](/kedro.pipeline.Pipeline) objects. For example, the pipeline registry in the [Kedro starter for the completed spaceflights tutorial](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights) could define the following `register_pipelines()` function that exposes the data processing pipeline, the data science pipeline, and a third, default pipeline that combines both of the aforementioned pipelines:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    data_processing_pipeline = dp.create_pipeline()
    data_science_pipeline = ds.create_pipeline()

    return {
        "__default__": data_processing_pipeline + data_science_pipeline,
        "data_processing": data_processing_pipeline,
        "data_science": data_science_pipeline,
    }
```

```{note}
The order in which you add the pipelines together is not significant (`data_science_pipeline + data_processing_pipeline` would produce the same result), since Kedro automatically detects the data-centric execution order for all the nodes in the resulting pipeline.
```

## Pipeline autodiscovery

In the above example, you need to update the `register_pipelines()` function whenever you create a pipeline that should be returned as part of the project's pipelines. Since Kedro 0.18.3, you can achieve the same result with less code using `find_pipelines()`[/kedro.framework.project.find_pipelines]:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Since Kedro 0.18.3, projects can use the ``find_pipelines`` function
    to autodiscover pipelines. However, projects that require more fine-
    grained control can still construct the pipeline mapping without it.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines
```

Under the hood, the `find_pipelines()` function traverses the `src/<package_name>/pipelines/` directory and returns a mapping from pipeline directory name to [`Pipeline`](/kedro.pipeline.Pipeline) object by:

1. Importing the `<package_name>.pipelines.<pipeline_name>` module
2. Calling the `create_pipeline()` function exposed by the `<package_name>.pipelines.<pipeline_name>` module
3. Validating that the constructed object is a [`Pipeline`](/kedro.pipeline.Pipeline)

If any of these steps fail, `find_pipelines()` raises an appropriate warning and skips the current pipeline but continues traversal.

The mapping returned by `find_pipelines()` can be modified. For example, to add a data engineering pipeline that isn't part of the default pipeline, add it to the dictionary *after* constructing the default pipeline:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Since Kedro 0.18.3, projects can use the ``find_pipelines`` function
    to autodiscover pipelines. However, projects that require more fine-
    grained control can still construct the pipeline mapping without it.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["__default__"] = sum(pipelines.values())
    pipelines["data_engineering"] = pipeline(
        pipelines["data_processing"], namespace="data_engineering"
    )
    return pipelines
```
