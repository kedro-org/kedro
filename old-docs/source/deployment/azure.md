# Azure ML pipelines

## `kedro-azureml` plugin

For deployment to Azure ML pipelines, you should [consult the documentation](https://kedro-azureml.readthedocs.io/en/stable/source/03_quickstart.html) for the [`kedro-azureml` plugin](https://github.com/getindata/kedro-azureml) from GetInData | Part of Xebia that enables you to run your code on Azure ML Pipelines in a fully managed fashion.

The plugin supports both: docker-based workflows and code-upload workflows.
Besides that, kedro-azureml also supports distributed training in PyTorch/TensorFlow/MPI and works well with Azure ML native MLflow integration.
