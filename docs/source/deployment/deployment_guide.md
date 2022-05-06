# Deployment guide

## Deployment choices

Your choice of deployment method will depend on a number of factors. In this section we provide a number of guides for different approaches.

If you decide to deploy your Kedro project on a single machine, you should consult our [guide to single-machine deployment](single_machine.md), and decide whether to [use Docker for container-based deployment](./single_machine.md#container-based) or to use [package-based deployment](./single_machine.md#package-based) or to [use the CLI to clone and deploy](./single_machine.md#cli-based) your codebase to a server.

If your pipeline is sizeable, you will want to run parts of it on separate machines, so will need to consult our [guide to distributed deployment](distributed.md).

We also provide information to help you deploy to the following:

* to [Argo Workflows](argo.md)
* to [Prefect](prefect.md)
* to [Kubeflow Workflows](kubeflow.md)
* to [AWS Batch](aws_batch.md)
* to [Databricks](databricks.md)
* to [Dask](dask.md)

<!--- There has to be some non-link text in the bullets above, if it's just links, there's a Sphinx bug that fails the build process-->

In addition, we also provide instructions on [how to integrate a Kedro project with Amazon SageMaker](aws_sagemaker.md).

```{mermaid}
flowchart TD
    A{Can your Kedro pipeline run on a single machine?} -- YES --> B[Consult the single-machine deployment guide];
    B --> C{Do you have Docker on your machine?};
    C -- YES --> D[Use a container-based approach];
    C -- NO --> E[Use the CLI or package mode];
    A -- NO --> F[Consult the distributed deployment guide];
    F --> G["What distributed platform are you using?<br/><br/>Check out the guides for:<br/><br/><li>Argo</li><li>Prefect</li><li>Kubeflow Pipelines</li><li>AWS Batch</li><li>Databricks</li><li>Dask</li>"];
    style G text-align:left
    H["Does (part of) your pipeline integrate with Amazon SageMaker?<br/><br/>Read the SageMaker integration guide"];
    style H text-align:left
```
