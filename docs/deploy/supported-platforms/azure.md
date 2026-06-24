# Azure ML pipelines

## `kedro-azureml` plugin

For deployment to Azure ML pipelines, see the [`kedro-azureml` plugin](https://github.com/getindata/kedro-azureml) from GetInData | Part of Xebia. This plugin enables you to run your code on Azure ML Pipelines in a fully managed fashion. For setup steps, [consult the documentation](https://kedro-azureml.readthedocs.io/en/stable/source/03_quickstart.html).

The plugin supports both Docker-based workflows and code-upload workflows. It also supports distributed training in PyTorch, TensorFlow, and MPI, and works well with the Azure ML native MLflow integration.
