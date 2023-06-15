# Choosing the Right Kedro Workflow for Databricks

Databricks offers integration with Kedro through three principal workflows:

- Use a Databricks workspace to develop a Kedro project.
- Use an IDE, dbx and Databricks Repos to develop a Kedro project.
- Use a Databricks job to deploy a Kedro project.

To enhance your development experience, it is crucial to choose the workflow that best fits your project's needs. Let's break down the advantages and use-cases of each workflow to help you make an informed decision.

## [Use a Databricks workspace to develop a Kedro project](./databricks_notebooks_development_workflow.md)

This workflow is crafted for those who enjoy developing and testing their projects directly within notebooks. If you wish to avoid the overhead of setting up and syncing a local environment with Databricks, then this is your workflow. The flexibility for quick iterations is there, though transitioning to a [job-based deployment](#databricks-deployment-workflow) might be necessary when preparing your project for production.

## [Use an IDE, dbx and Databricks Repos to develop a Kedro project](./databricks_ide_development_workflow.md)

If you're in the early stages of learning Kedro, or your project requires constant testing and adjustments, this workflow is the way to go. This workflow allows you to make the most of your local IDE's capabilities for faster, error-free development. It is perfect for development stages and can handle production deployment, but you might need to transition to the Deployment Workflow to fully optimise your project for production.

(databricks-deployment-workflow)=
## [Use a Databricks job to deploy a Kedro project](./databricks_deployment_workflow.md)

This workflow is the go-to choice when dealing with complex project requirements that call for a high degree of structure and reproducibility. It's your best bet for a production setup given its support for CI/CD, automated/scheduled runs and other advanced use-cases. That being said, it might not be the ideal choice for projects requiring quick iterations due to its relatively rigid nature.

## Decision-Making Flowchart

Here's a flowchart to guide you in choosing the right workflow:

```{mermaid}
graph TD
  A[Start] --> B{Do you prefer developing your projects in notebooks?}
  B -->|Yes| C[Use a Databricks workspace to develop a Kedro project]
  B -->|No| D{Are you a beginner with Kedro?}
  D -->|Yes| E[Use an IDE, dbx and Databricks Repos to develop a Kedro project]
  D -->|No| F{Do you have advanced project requirements<br>e.g. CI/CD, Scheduling, Production Ready, Complex Pipelines, etc.?}
  F -->|Yes| G{Is rapid development needed for your project needs?}
  F -->|No| H[Use a Databricks job to deploy a Kedro project]
  G -->|Yes| I[Use an IDE, dbx and Databricks Repos to develop a Kedro project]
  G -->|No| J[Use a Databricks job to deploy a Kedro project]
```

Remember, the right workflow is the one that aligns best with your project's requirements, whether that's quick development, notebook-based coding, or a production-ready setup. Make sure to consider these factors alongside your comfort level with Kedro when making your decision.
