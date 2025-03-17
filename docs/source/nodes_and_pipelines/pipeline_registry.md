# The pipeline registry

Projects generated using Kedro 0.17.2 or later define their pipelines in `src/<package_name>/pipeline_registry.py`. This, in turn, populates the `pipelines` variable in {py:mod}`~kedro.framework.project` that the Kedro CLI and plugins use to access project pipelines. The `pipeline_registry` module must contain a top-level `register_pipelines()` function that returns a mapping from pipeline names to {py:class}`~kedro.pipeline.Pipeline` objects. For example, the [pipeline registry in the Kedro starter for the completed spaceflights tutorial](https://github.com/kedro-org/kedro-starters/blob/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/pipeline_registry.py) could define the following `register_pipelines()` function that exposes the data processing pipeline, the data science pipeline, and a third, default pipeline that combines both of the aforementioned pipelines:

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

In the above example, you need to update the `register_pipelines()` function whenever you create a pipeline that should be returned as part of the project's pipelines. Since Kedro 0.18.3, you can achieve the same result with less code using {py:meth}` find_pipelines() <kedro.framework.project.find_pipelines>`. The [updated pipeline registry](https://github.com/kedro-org/kedro-starters/blob/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/pipeline_registry.py) contains no project-specific code:

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

Under the hood, the `find_pipelines()` function traverses the `src/<package_name>/pipelines/` directory and returns a mapping from pipeline directory name to {py:class}`~kedro.pipeline.Pipeline` object by:

1. Importing the `<package_name>.pipelines.<pipeline_name>` module
2. Calling the `create_pipeline()` function exposed by the `<package_name>.pipelines.<pipeline_name>` module
3. Validating that the constructed object is a {py:class}`~kedro.pipeline.Pipeline`

By default, if any of these steps fail, `find_pipelines()` (or `find_pipelines(raise_errors=False)`) raises an appropriate warning and skips the current pipeline but continues traversal. During development, this enables you to run your project with some pipelines, even if other pipelines are broken or works in progress.

If you specify `find_pipelines(raise_errors=True)`, the autodiscovery process will fail upon the first error. In production, this ensures errors are caught up front, and pipelines do not get excluded accidentally.

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
        pipelines["data_processing"], tags="data_engineering"
    )
    return pipelines
```
```{note}
In the case above, `kedro run --tags data_engineering` will not run the data engineering pipeline, as it is not part of the default pipeline. To run the data engineering pipeline, you need to specify `kedro run --pipeline data_engineering --tags data_engineering`.
```
On the other hand, you can also modify pipelines *before* assigning `pipelines["__default__"] = sum(pipelines.values())` which includes it in the default pipeline. For example, you can update the `data_processing` pipeline with the `data_engineering` tag in the `pipeline_registry.py` and also include this change in the default pipeline:

```python
def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["data_processing"] = pipeline(
        pipelines["data_processing"], tags="data_engineering"
    )
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines
```
