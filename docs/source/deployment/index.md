# Deployment

## Deployment choices

Your choice of deployment method will depend on various factors. In this section we provide guides for different approaches.

If you decide to deploy your Kedro project on a single machine, you should consult our [guide to single-machine deployment](single_machine.md), and decide whether to [use Docker for container-based deployment](./single_machine.md#container-based) or to use [package-based deployment](./single_machine.md#package-based) or to [use the CLI to clone and deploy](./single_machine.md#cli-based) your codebase to a server.

If your pipeline is sizeable, you will want to run parts of it on separate machines, so will need to consult our [guide to distributed deployment](distributed.md).

We also provide information to help you deploy to the following:

* to [Airflow](airflow_astronomer.md)
* to [AWS SageMaker](aws_sagemaker.md)
* to [AWS Step functions](aws_step_functions.md)
* to [Azure](azure.md)
* to [Dask](dask.md)
* to [Databricks](../integrations/databricks_workspace.md)
* to [Kubeflow Workflows](kubeflow.md)
* to [Prefect](prefect.md)
* to [Vertex AI](vertexai.md)

``` {warning}
We also have legacy documentation pages for the following deployment targets, but these have not been tested against recent Kedro releases and we cannot guarantee them:

* for [Argo Workflows](argo.md)
* for [AWS Batch](aws_batch.md)
```

<!--- There has to be some non-link text in the bullets above, if it's just links, there's a Sphinx bug that fails the build process-->

In addition, we also provide instructions on [how to integrate a Kedro project with Amazon SageMaker](aws_sagemaker.md).

```{mermaid}
flowchart TD
    A{Can your Kedro pipeline run on a single machine?} -- YES --> B[Consult the single-machine deployment guide];
    B --> C{Do you have Docker on your machine?};
    C -- YES --> D[Use a container-based approach];
    C -- NO --> E[Use the CLI or package mode];
    A -- NO --> F[Consult the distributed deployment guide];
    F --> G["What distributed platform are you using?<br/><br/>Check out the guides for:<br/><br/><li>Airflow</li><li>AWS SageMaker</li><li>AWS Step functions</li><li>Azure</li><li>Dask</li><li>Databricks</li><li>Kubeflow Workflows</li><li>Prefect</li><li>Vertex AI</li>"];
    style G text-align:left
    H["Does (part of) your pipeline integrate with Amazon SageMaker?<br/><br/>Read the SageMaker integration guide"];
    style H text-align:left
```

## Deployment guides

```{toctree}
:maxdepth: 1

single_machine
distributed
airflow_astronomer
aws_sagemaker
aws_step_functions
azure
dask
kubeflow
prefect
vertexai
argo
aws_batch
```
