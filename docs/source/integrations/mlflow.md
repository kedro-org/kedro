# How to add MLflow to your Kedro workflow

[MLflow](https://mlflow.org/) is an open-source platform for managing the end-to-end machine learning lifecycle.
It provides tools for tracking experiments, packaging code into reproducible runs, and sharing and deploying models.
MLflow supports machine learning frameworks such as TensorFlow, PyTorch, and scikit-learn.

Adding MLflow to a Kedro project enables you to track and manage your machine learning experiments and models.
For example, you can log metrics, parameters, and artifacts from your Kedro pipeline runs to MLflow, then compare and reproduce the results. When collaborating with others on a Kedro project, MLflow's model registry and deployment tools help you to share and deploy machine learning models.

## Prerequisites

You will need the following:

- A working Kedro project in a virtual environment. The examples in this document assume the `spaceflights-pandas-viz` starter.
  If you're unfamiliar with the Spaceflights project, check out [our tutorial](/tutorial/spaceflights_tutorial).
- The MLflow client installed into the same virtual environment. For the purposes of this tutorial,
  you can use MLflow {external+mlflow:doc}`in its simplest configuration <tracking>`.

To set yourself up, create a new Kedro project:

```
$ kedro new --starter=spaceflights-pandas-viz --name spaceflights-mlflow
$ cd spaceflights-mlflow
$ python -m venv && source .venv/bin/activate
(.venv) $ pip install -r requirements.txt
```

And then launch the UI locally from the root of your directory as follows:

```
(.venv) $ pip install mlflow
(.venv) $ mlflow ui --backend-store-uri ./mlflow_runs
```

This will make MLflow record metadata and artifacts for each run
to a local directory called `mlflow_runs`.

:::{note}
If you want to use a more sophisticated setup,
have a look at the documentation of
[MLflow tracking server](https://mlflow.org/docs/latest/tracking/server),
{external+mlflow:doc}`the official MLflow tracking server 5 minute overview <getting-started/tracking-server-overview/index>`,
and {external+mlflow:ref}`the MLflow tracking server documentation <logging_to_a_tracking_server>`.
:::

## Simple use cases

Although MLflow works best when working with machine learning (ML) and AI pipelines,
you can track your regular Kedro runs as experiments in MLflow even if they do not use ML.

This section explains how you can use the [`kedro-mlflow`](https://kedro-mlflow.readthedocs.io/) plugin
to track your Kedro pipelines in MLflow in a straightforward way.

### Easy tracking of Kedro runs in MLflow using `kedro-mlflow`

To start using `kedro-mlflow`, install it first:

```
pip install kedro-mlflow
```

In recent versions of Kedro, this will already register the `kedro-mlflow` Hooks for you.

Next, create a `mlflow.yml` configuration file in your `conf/local` directory
that configures where the MLflow runs are stored,
consistent with how you launched the `mlflow ui` command:

```yaml
server:
  mlflow_tracking_uri: mlflow_runs
```

From this point, when you execute `kedro run` you will see the logs coming from `kedro-mlflow`:

```
[06/04/24 09:52:53] INFO     Kedro project spaceflights-mlflow                                     session.py:324
                    INFO     Registering new custom resolver: 'km.random_name'                  mlflow_hook.py:65
                    INFO     The 'tracking_uri' key in mlflow.yml is relative          kedro_mlflow_config.py:260
                             ('server.mlflow_(tracking|registry)_uri = mlflow_runs').
                             It is converted to a valid uri:
                             'file:///Users/juan_cano/Projects/QuantumBlackLabs/kedro-
                             mlflow-playground/spaceflights-mlflow/mlflow_runs'
```

If you open your tracking server UI you will observe a result like this:

```{image} ../meta/images/complete-mlflow-tracking-kedro-mlflow.png
:alt: Complete MLflow tracking with kedro-mlflow
:width: 80%
:align: center
```

Notice that `kedro-mlflow` used a subset of the `run_params` as tags for the MLflow run,
and logged the Kedro parameters as MLflow parameters.

Check out {external+kedro-mlflow:doc}`the official kedro-mlflow tutorial <source/03_getting_started/02_first_steps>`
for more detailed steps.

### Artifact tracking in MLflow using `kedro-mlflow`

`kedro-mlflow` provides some out-of-the-box artifact tracking capabilities
that connect your Kedro project with your MLflow deployment, such as `MlflowArtifactDataset`,
which can be used to wrap any of your existing Kedro datasets.

Use of this dataset has the advantage that the preview capabilities of the MLflow UI can be used.

:::{warning}
This will work for datasets that are outputs of a node,
and will have no effect for datasets that are free inputs (hence are only loaded).
:::

For example, if you modify the a `matplotlib.MatplotlibWriter` dataset like this:

```diff
 # conf/base/catalog.yml

 dummy_confusion_matrix:
-  type: matplotlib.MatplotlibWriter
-  filepath: data/08_reporting/dummy_confusion_matrix.png
-  versioned: true
+  type: kedro_mlflow.io.artifacts.MlflowArtifactDataset
+  dataset:
+    type: matplotlib.MatplotlibWriter
+    filepath: data/08_reporting/dummy_confusion_matrix.png
```

Then the image would be logged as part of the artifacts of the run
and you would be able to preview it in the MLflow web UI:

```{image} ../meta/images/mlflow-artifact-preview-image.png
:alt: MLflow image preview thanks to the artifact tracking capabilities of kedro-mlflow
:width: 80%
:align: center
```

:::{warning}
If you get a `Failed while saving data to dataset MlflowMatplotlibWriter` error,
it's probably because you had already executed `kedro run` while the dataset was marked as `versioned: true`.
The solution is to cleanup the old `data/08_reporting/dummy_confusion_matrix.png` directory.
:::

Check out {external+kedro-mlflow:doc}`the official kedro-mlflow documentation on versioning Kedro datasets <source/04_experimentation_tracking/03_version_datasets>`
for more information.

### Model registry in MLflow using `kedro-mlflow`

If your Kedro pipeline trains a machine learning model, you can track those models in MLflow
so that you can manage and deploy them.
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

The `kedro-mlflow` Hook will log the model as part of the run
in {external+mlflow:doc}`the standard MLflow Model format <models>`.

If you also want to _register_ it
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

To load a model from a specific run, you can specify the `run_id`.
For that, you can make use of {ref}`runtime parameters <runtime-params>`:

```{code-block} yaml
:emphasize-lines: 13

# Add the intermediate datasets to run only the inference
X_test:
  type: pandas.ParquetDataset
  filepath: data/05_model_input/X_test.parquet

y_test:
  type: pandas.CSVDataset  # https://github.com/pandas-dev/pandas/issues/54638
  filepath: data/05_model_input/y_test.csv

regressor:
  type: kedro_mlflow.io.models.MlflowModelTrackingDataset
  flavor: mlflow.sklearn
  run_id: ${runtime_params:mlflow_run_id,null}
  save_args:
    registered_model_name: spaceflights-regressor
```

And specify the MLflow run id on the command line as follows:

```
$ kedro run --to-outputs=X_test,y_test
...
$ kedro run --from-nodes=evaluate_model_node --params mlflow_run_id=4cba84...
```

:::{note}
Notice that MLflow runs are immutable for reproducibility purposes,
therefore you cannot _save_ a model in an existing run.
:::

## Advanced use cases

### Track additional metadata of Kedro runs in MLflow using Hooks

So far, `kedro-mlflow` has proven abundantly useful already.
And yet, you might have the need to track additional metadata in the run.

One possible way of doing it is using the {py:meth}`~kedro.framework.hooks.specs.PipelineSpecs.before_pipeline_run` Hook
to log the `run_params` passed to the Hook.
An implementation would look as follows:

```python
# src/spaceflights_mlflow/hooks.py

import typing as t
import logging

import mlflow
from kedro.framework.hooks import hook_impl

logger = logging.getLogger(__name__)


class ExtraMLflowHooks:
    @hook_impl
    def before_pipeline_run(self, run_params: dict[str, t.Any]):
        logger.info("Logging extra metadata to MLflow")
        mlflow.set_tags({
            "pipeline": run_params["pipeline_name"] or "__default__",
            "custom_version": "0.1.0",
        })
```

And then enable your custom hook in `settings.py`:

```python
# src/spaceflights_mlflow/settings.py
...
from .hooks import ExtraMLflowHooks

HOOKS = (ExtraMLflowHooks(),)
...
```

After enabling this custom Hook, you can execute `kedro run`, and see something like this in the logs:

```
...
[06/04/24 10:44:25] INFO     Logging extra metadata to MLflow                                         hooks.py:13
...
```

If you open your tracking server UI you will observe a result like this:

```{image} ../meta/images/extra-mlflow-tracking.png
:alt: Simple MLflow tracking
:width: 50%
:align: center
```

### Tracking Kedro in MLflow using the Python API

If you are running Kedro programmatically using the Python API,
you can log your runs using the MLflow "fluent" API.

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

If you want more flexibility or to log extra parameters,
you might need to run the Kedro pipelines manually yourself.
