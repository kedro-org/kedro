# The pipeline registry

Projects generated using Kedro 0.17.2 or later define their pipelines in `src/<package_name>/pipeline_registry.py`. This, in turn, populates the `pipelines` variable in [`kedro.framework.project`](/kedro.framework.project) that the Kedro CLI and plugins use to access project pipelines. The `pipeline_registry` module must contain a top-level `register_pipelines()` function that returns a mapping from pipeline names to [`Pipeline`](/kedro.pipeline.Pipeline) objects. For example, the [pipeline registry in the Kedro starter for the completed spaceflights tutorial](https://github.com/kedro-org/kedro-starters/blob/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/pipeline_registry.py) could define the following `register_pipelines()` function that exposes the data processing pipeline, the data science pipeline, and a third, default pipeline that combines both of the aforementioned pipelines:

```python
import spaceflights.pipelines.data_processing as dp
import spaceflights.pipelines.data_science as ds


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

As a reminder, [running `kedro run` without the `--pipeline` option runs the default pipeline](./run_a_pipeline.md#run-a-pipeline-by-name).

```{note}
The order in which you add the pipelines together is not significant (`data_science_pipeline + data_processing_pipeline` would produce the same result), since Kedro automatically detects the data-centric execution order for all the nodes in the resulting pipeline.
```

## Pipeline autodiscovery

In the above example, you need to update the `register_pipelines()` function whenever you create a pipeline that should be returned as part of the project's pipelines. Since Kedro 0.18.3, you can achieve the same result with less code using [`find_pipelines()`](/kedro.framework.project.find_pipelines). The [updated pipeline registry](https://github.com/kedro-org/kedro-starters/blob/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/pipeline_registry.py) contains no project-specific code:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

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

The mapping returned by `find_pipelines()` can be modified, meaning you are not limited to the pipelines returned by each of the `create_pipeline()` functions found above. For example, to add a data engineering pipeline that isn't part of the default pipeline, add it to the dictionary *after* constructing the default pipeline:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

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

On the other hand, adding the same pipeline *before* assigning `pipelines["__default__"] = sum(pipelines.values())` includes it in the default pipeline, so the data engineering pipeline will be run if `kedro run` is called without specifying a pipeline name:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["data_engineering"] = pipeline(
        pipelines["data_processing"], namespace="data_engineering"
    )
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines
```
