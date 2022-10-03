# Experiment tracking

```{warning}
Experiment tracking in Kedro is launched as beta functionality. We encourage everyone to try it out and give us feedback so that we can settle on the final implementation of the feature.
```

Experiment tracking is a way to record all information that you would need to recreate and analyse a data science experiment. We think of it as logging for parameters, metrics, models and other dataset types.
Kedro currently supports parts of this functionality. For example, it’s possible to log parameters as part of your codebase and snapshot models and other artefacts like plots with Kedro’s versioning capabilities for datasets.
However, Kedro was missing a way to log metrics and capture all this logged data as a timestamped run of an experiment. It was also missing a way for users to visualise, discover and compare this logged data.

Experiment tracking in Kedro adds in the missing pieces and will be developed incrementally.

The following section outlines the setup within your Kedro project to enable experiment tracking. You can also refer to the [tutorial on setting up experiment tracking](../tutorial/set_up_experiment_tracking.md) for a step-by-step process to access your tracking datasets on Kedro-Viz.

## Enable experiment tracking

### Set up the session store

In the domain of experiment tracking, each pipeline run is considered a session. A session store records all related metadata for each pipeline run, from logged metrics to other run-related data such as timestamp, git username and branch. The session store is a [SQLite](https://www.sqlite.org/index.html) database that is generated during your first pipeline run after it has been set up in your project.

To set up the session store, go to the `src/settings.py` file and add the following:

```python
from kedro_viz.integrations.kedro.sqlite_store import SQLiteStore
from pathlib import Path

SESSION_STORE_CLASS = SQLiteStore
SESSION_STORE_ARGS = {"path": str(Path(__file__).parents[2] / "data")}
```

This will specify the creation of the `SQLiteStore` under the `/data` subfolder, using the `SQLiteStore` setup from your installed Kedro-Viz plugin.

Please ensure that your installed version of Kedro-Viz is at least version 4.1.1 onwards. This step is crucial to enable experiment tracking features on Kedro-Viz, as it is the database used to serve all run data to the Kedro-Viz front-end.

### Set up tracking datasets

Use either one of the [`tracking.MetricsDataSet`](/kedro.extras.datasets.tracking.MetricsDataSet) or [`tracking.JSONDataSet`](/kedro.extras.datasets.tracking.JSONDataSet) in your data catalog. These datasets are versioned by default to ensure a historical record is kept of the logged data.
The `tracking.MetricsDataSet` should be used for tracking numerical metrics and the `tracking.JSONDataSet` can be used for tracking any other JSON-compatible data. In Kedro-Viz these datasets will be visualised in the metadata side panel.

Below is an example of how to add experiment tracking to your pipeline. Add a `tracking.MetricsDataSet` and/or `tracking.JSONDataSet` to your `catalog.yml`:
```yaml
metrics:
  type: tracking.MetricsDataSet
  filepath: data/09_tracking/metrics.json

```

### Set up your nodes and pipelines to log metrics

Add a node that returns the data to be tracked. The `report_accuracy` node below returns metrics.

```python
# nodes.py
from sklearn.metrics import accuracy_score


def report_accuracy():
    """Node for reporting the accuracy of the predictions."""
    test_y = [0, 2, 1, 3]
    predictions = [0, 1, 2, 3]

    accuracy = accuracy_score(test_y, predictions)
    # Return the accuracy of the model
    return {"accuracy": accuracy}
```

Add the node to your pipeline and ensure that the output name matches the name of the dataset added to your catalog.

```python
# pipeline.py
from kedro.pipeline import Pipeline, node, pipeline
from .nodes import report_accuracy


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                report_accuracy,
                [],
                "metrics",
                name="report",
            ),
        ]
    )
```

## Community solutions
You can find more solutions for experiment tracking developed by the Kedro community on the [plugins page](../extend_kedro/plugins.md#community-developed-plugins).
