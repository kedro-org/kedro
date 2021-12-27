# Deployment guide

## Deployment choices

Your choice of deployment method will depend on a number of factors. In this section we provide a number of guides for different approaches.

If you decide to deploy your Kedro project on a single machine, you should consult our [guide to single-machine deployment](02_single_machine.md), and decide whether to [use Docker for container-based deployment](./02_single_machine.md#container-based) or to use [package-based deployment](./02_single_machine.md#package-based) or to [use the CLI to clone and deploy](./02_single_machine.md#cli-based) your codebase to a server.

If your pipeline is sizeable, you will want to run parts of it on separate machines, so will need to consult our [guide to distributed deployment](03_distributed.md).

We also provide information to help you deploy to the following:

* to [Argo Workflows](04_argo.md)
* to [Prefect](05_prefect.md)
* to [Kubeflow Workflows](06_kubeflow.md)
* to [AWS Batch](07_aws_batch.md)
* to [Databricks](08_databricks.md)
* to [Dask](12_dask.md)

<!--- There has to be some non-link text in the bullets above, if it's just links, there's a Sphinx bug that fails the build process-->

In addition, we also provide instructions on [how to integrate a Kedro project with Amazon SageMaker](09_aws_sagemaker.md).

![](../meta/images/deployments.png)  <!-- TODO(deepyaman): Add Dask to deployment flowchart. -->
