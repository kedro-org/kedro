# Using Kedro and MLflow

MLflow is an open-source platform for managing the end-to-end machine learning lifecycle.
It provides tools for tracking experiments, packaging code into reproducible runs, and sharing and deploying models.
MLflow also supports multiple machine learning frameworks, including TensorFlow, PyTorch, and scikit-learn.

MLflow is an excellent companion for your Kedro projects because it allows you to easily track and manage your machine learning experiments and models.
By integrating MLflow with Kedro, you can seamlessly log metrics, parameters, and artifacts from your Kedro pipeline runs to MLflow,
making it easy to compare and reproduce results.
Additionally, MLflow's model registry and deployment tools make it easy to share and deploy your Kedro models with others.

## Preparation

You will need

- A working Kedro project.
- The MLflow client properly installed in your project: `pip install mlflow`.
- (Recommended) An MLflow Tracking Server, which will allow you to quickly inspect the runs with a user-friendly web interface.

For the Kedro project, the examples in this document assume the `spaceflights-pandas-viz` starter.

The MLflow Tracking Server is optional, but highly recommended,
even if you're working locally on a solo project.
This document will assume that you have a running Tracking Server,
whether it's a local one run by yourself or a remote one running on another machine or provided by a cloud vendor.
You will need to configure your client properly,
either by setting the `MLFLOW_TRACKING_URI` environment variable
or by using the {external+mlflow:py:func}`mlflow.set_tracking_uri` function.
Read {external+mlflow:doc}`the official MLflow Tracking Server 5 minute overview <getting-started/tracking-server-overview/index>`
for a list of available options,
and {external+mlflow:ref}`the MLflow Tracking Server documentation <logging_to_a_tracking_server>`
for detailed configuration instructions.

## Use cases

There are different use cases for which you might want to use MLflow,
many of which are already covered by the [`kedro-mlflow`](https://kedro-mlflow.readthedocs.io/) plugin.
In this document you will learn how to implement them yourself in a simplified form,
and also how `kedro-mlflow` can do the hard work for you.

### Simple tracking of Kedro runs in MLflow using hooks

Even though MLflow works best when working with machine learning and AI pipelines,
you can track your regular Kedro runs as experiments in MLflow even if they have nothing to do with ML.

One possible way of doing it is using the {py:meth}`~kedro.framework.hooks.specs.PipelineSpecs.before_pipeline_run` hook
to log the `run_params` passed to the hook.
Here is how such an implementation would look like:

```python
import typing as t

import mlflow
from kedro.framework.hooks import hook_impl
from mlflow.entities import RunStatus


class MLflowHooks:
    @hook_impl
    def before_pipeline_run(self, run_params: dict[str, t.Any]):
        logger.info("Logging run parameters to MLflow")
        mlflow.log_params(run_params)
        mlflow.set_tags({"pipeline": run_params["pipeline_name"] or "__default__"})

    @hook_impl
    def on_pipeline_error(self):
        logger.error("Logging error to MLflow")
        mlflow.end_run(RunStatus.to_string(RunStatus.FAILED))
```

Notice that there is also extra code to mark the run as failed if there is any error.

After enabling this custom hook, you can execute `kedro run`
and you will see something like this in the logs:

```
[05/06/24 12:43:30] INFO     Kedro project spaceflights-mlflow             session.py:324
[05/06/24 12:43:31] INFO     Logging run parameters to MLFlow                 hooks.py:18
...
```

And if you open your Tracking Server UI you will observe a result similar to this:

```{image} ../meta/images/simple-mlflow-tracking1.png
:alt: Simple MLflow tracking
:width: 50%
:align: center
```

```{image} ../meta/images/simple-mlflow-tracking2.png
:alt: Simple MLflow tracking
:width: 50%
:align: center
```

Notice that these "parameters" do not include the Kedro parameters as defined in `parameters*.yml`.
To log the actual Kedro parameters, you can continue writing a custom hook
or use the `kedro-mlflow` plugin instead, as described in the following section.

### Complete tracking of Kedro runs in MLflow using `kedro-mlflow`

You could make the code snippet above more complex.
However, at some point you might want to leverage all the work that the `kedro-mlflow` plugin
can already do for you.

To start using `kedro-mlflow`, the only required step is to install it:

```
pip install kedro-mlflow
```

In modern versions of Kedro, this will already register the `kedro-mlflow` hooks for you.

:::{note}
If you implemented your custom `MLflowHooks` as described in the previous section,
consider disabling them to avoid logging the runs twice.
:::

`kedro-mlflow` will use a subset of the `run_params` as tags for the MLflow run,
and log the Kedro parameters as MLflow parameters:

```{image} ../meta/images/complete-mlflow-tracking-kedro-mlflow.png
:alt: Complete MLflow tracking with kedro-mlflow
:width: 50%
:align: center
```

Check out {external+kedro-mlflow:doc}`the official kedro-mlflow tutorial <source/03_getting_started/02_first_steps>`
for more detailed steps.

Notice that `kedro-mlflow` assumes 1 Kedro project = 1 MLflow experiment.
If this does not suit your use case, consider pursuing a more customised approach
like the one described in the previous section.

### Tracking Kedro in MLflow using the Python API

If you are running Kedro programmatically using the Python API,
you can easily log your runs using the MLflow "fluent" API.

For example, taking the {doc}`lifecycle management example </kedro_project_setup/session>`
as a starting point:

```python
from pathlib import Path

import mlflow
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

bootstrap_project(Path.cwd())

mlflow.set_experiment("Kedro Spaceflights test")

with KedroSession.create() as session:
    with mlflow.start_run():
        mlflow.set_tag("session_id", session.session_id)
        session.run()
```

Notice that, if you want more flexibility or to log extra parameters,
you might need to run the Kedro pipelines manually yourself.

### Simple artifact tracking in MLflow using hooks

MLflow also helps you store "artifacts" associated with a run,
which include compressed model weights, images, and other typically large files.

For example, you can use the {py:meth}`~kedro.framework.hooks.specs.DatasetSpecs.before_dataset_saved` hook
to store a pickled version of the data, as follows:

```python
import pickle
import tempfile
import typing as t
from pathlib import Path


class ArtifactTrackingHooks:
    @hook_impl
    def before_dataset_saved(self, dataset_name: str, data: t.Any):
        logger.info(f"Logging dataset '{dataset_name}' to MLFlow")

        # Serialise object to temporary directory and log it to MLFlow
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / f"{dataset_name}.pkl"
            try:
                with open(file_path, "wb") as fh:
                    pickle.dump(data, fh)
            except Exception:
                logger.error(f"Failed to pickle dataset '{dataset_name}'")
            else:
                mlflow.log_artifact(file_path)
```

Which will result in something like this:

```{image} ../meta/images/mlflow-pickle-artifact.png
:alt: Tracking artifacts as pickles in MLflow
:width: 50%
:align: center
```

Notice though that storing artifacts as Python pickles
prevents you from fully using MLflow native preview capabilities.

### Artifact tracking in MLflow using `kedro-mlflow`

Again, `kedro-mlflow` provides some out-of-the-box artifact tracking capabilities
that connect your Kedro project with your MLflow deployment.

To that end, introduces a special `MlflowArtifactDataset`
that can be used to wrap any of your existing Kedro datasets.
This has the advantage that the preview capabilities of the MLflow UI can be used.

:::{warning}
This will work for datasets that are outputs of a node,
and will have no effect for datasets that are free inputs (hence are only loaded).
:::

For example, if you wrap a `matplotlib.MatplotlibWriter` dataset like this:

```yaml
dummy_confusion_matrix:
  type: kedro_mlflow.io.artifacts.MlflowArtifactDataset
  dataset:
    type: matplotlib.MatplotlibWriter
    filepath: data/08_reporting/dummy_confusion_matrix.png
```

Then the image would be logged as part of the artifacts of the run
and you would be able to preview it in the MLflow web UI:

```{image} ../meta/images/mlflow-artifact-preview-image.png
:alt: MLflow image preview thanks to the artifact tracking capabilities of kedro-mlflow
:width: 80%
:align: center
```

Check out {external+kedro-mlflow:doc}`the official kedro-mlflow documentation on versioning Kedro datasets <source/04_experimentation_tracking/03_version_datasets>`
for more information.

### Model registry in MLflow using `kedro-mlflow`

Finally, if your Kedro pipeline trains a machine learning model, you can track those models in MLflow
so that you can easily manage and deploy them.
The `kedro-mlflow` plugin introduces a special artifact, `MlflowModelTrackingDataset`,
that you can use to load and save your models as MLflow artifacts.

For example, if you have a dataset corresponding to a scikit-learn model,
you can modify it as follows:

```diff
 regressor:
-  type: pickle.PickleDataset
-  filepath: data/06_models/regressor.pickle
-  versioned: true
+  type: kedro_mlflow.io.models.MlflowModelTrackingDataset
+  flavor: mlflow.sklearn
```

The `kedro-mlflow` hook will log the model as part of the run
in {external+mlflow:doc}`the standard MLflow Model format <models>`.

If, additionally, you want to _register_ it
(hence store it in the MLflow Model Registry)
you can add a `registered_model_name` parameter:

```{code-block} yaml
:emphasize-lines: 4-5

regressor:
  type: kedro_mlflow.io.models.MlflowModelTrackingDataset
  flavor: mlflow.sklearn
  save_args:
    registered_model_name: spaceflights-regressor
```

Then you will see it listed as a Registered Model:

```{image} ../meta/images/kedro-mlflow-registered-model.png
:alt: MLflow Model Registry listing one model registered with kedro-mlflow
:width: 80%
:align: center
```

:::{warning}
At the moment it's not straightforward to specify the `run_id`
to use a specific version of a model for inference within a Kedro pipeline,
see discussion on [this GitHub issue](https://github.com/Galileo-Galilei/kedro-mlflow/issues/549).
:::
