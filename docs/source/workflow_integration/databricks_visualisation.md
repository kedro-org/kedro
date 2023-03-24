# Running Kedro-Viz on Databricks

[Kedro-Viz](../visualisation/kedro-viz_visualisation.md) is a tool that allows you to visualise your Kedro pipeline. It is a standalone web application that runs on a web browser, it can be run on a local machine or on Databricks itself.

For Kedro-Viz to run with your Kedro project, you need to ensure that both the packages are installed in the same scope (notebook-scoped vs. cluster library). i.e. if you `%pip install kedro` from inside your notebook then you should also `%pip install kedro-viz` from inside your notebook.
If your cluster comes with Kedro installed on it as a library already then you should also add Kedro-Viz as a [cluster library](https://docs.microsoft.com/en-us/azure/databricks/libraries/cluster-libraries).

Kedro-Viz can then be launched in a new browser tab with the `%run_viz` line magic:
```ipython
In [2]: %run_viz
```
