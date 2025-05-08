# Deployment

## Overview

In this section we provide guides for different deployment methods; your choice  will depend on a range of factors.

If you decide to deploy your Kedro project onto a single machine, you should consult our [guide to single-machine deployment](single_machine.md), and decide whether to:

- [use Docker for container-based deployment](./single_machine.md#container-based)
- [use package-based deployment](./single_machine.md#package-based)
- [use the CLI to clone and deploy your codebase to a server](./single_machine.md#cli-based)

If your pipeline is sizeable, you may want to run it across separate machines, so will need to consult our [guide to distributed deployment](distributed.md).

```mermaid
flowchart TD
    A{Can your Kedro pipeline run on a single machine?} -- YES --> B[Consult the single-machine deployment guide]
    B --> C{Do you have Docker on your machine?}
    C -- YES --> D[Use a container-based approach]
    C -- NO --> E[Use the CLI or package mode]
    A -- NO --> F[Consult the distributed deployment guide]
    F --> G["What distributed platform are you using?<br/><br/>Check out the guides for:<br/><br/><li>Airflow</li><li>Amazon SageMaker</li><li>AWS Step functions</li><li>Azure</li><li>Dask</li><li>Databricks</li><li>Kubeflow Pipelines</li><li>Prefect</li><li>Vertex AI</li>"]
```

## Deployment Methods

This following pages provide information for deployment to, or integration with, the following:

- [Airflow](airflow.md)
- [Amazon SageMaker](amazon_sagemaker.md)
- [Amazon EMR Serverless](amazon_emr_serverless.md)
- [AWS Step functions](aws_step_functions.md)
- [Azure](azure.md)
- [Dask](dask.md)
- [Databricks](./databricks/index.md)
- [Kubeflow Pipelines](kubeflow.md)
- [Prefect](prefect.md)
- [Vertex AI](vertexai.md)

> **Warning**
> We also have legacy documentation pages for the following deployment targets, but these have not been tested against recent Kedro releases and we cannot guarantee them:
>
> - for [Argo Workflows](./supported-platforms/argo.md)
> - for [AWS Batch](./supported-platforms/aws_batch.md)

## Effective node grouping for deployment

Effectively grouping nodes in deployment makes pipelines easier to manage and update, improves performance by using resources more efficiently, and enables them to handle larger datasets as they scale across different deployment environments. To learn more about the best ways to group nodes using Pipelines, Tags, and Namespaces, follow our detailed guide:

- [Node Grouping in Kedro](nodes_grouping.md)
