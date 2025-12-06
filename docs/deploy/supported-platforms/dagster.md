# Dagster


## Why would you use Dagster?
Dagster is a modern Python data orchestration platform. For Kedro users, Dagster provides a powerful bridge between local development and production-grade data and machine learning pipelines. Dagster complements Kedro’s effective modular pipeline authoring, configuration management, and data catalog by enabling teams to build, schedule, and monitor workflows with enhanced observability and scalability. Key benefits of using Dagster with Kedro include:

- **Asset-first philosophy**: Dagster adopts an asset-first approach, treating datasets and models as first-class citizens. This aligns naturally with Kedro’s data catalog and node-based pipeline architecture. By mapping Kedro nodes and datasets to Dagster assets, you gain a clearer view of data lineage, dependencies, and the flow of transformations across your project.
- **Enhanced orchestration, scheduling, and observability**: Dagster offers rich orchestration capabilities with fine-grained control over scheduling, retries, and execution monitoring. From a Kedro perspective, this means turning your pipelines into fully observable assets with built-in dashboards for runs, logs, and asset materialisation thus providing transparency across your data lifecycle.
- **Scalability from local to production**: Dagster supports running pipelines locally for development and seamlessly scaling them to production environments using a variety of execution targets. Kedro users can experiment interactively within their existing environment and later deploy the same pipelines at scale without code changes.
- **Integration-friendly**: Dagster integrates readily with modern data stack tools ranging from dbt and Spark and to cloud storage and machine learning frameworks such as MLflow. This makes it a versatile choice for Kedro users looking to build end-to-end data workflows that connect various components of their data ecosystem.

## The `kedro-dagster` plugin
The `kedro-dagster` plugin by [Guillaume Tauzin](https://github.com/gtauzin) enables you to translate your Kedro project to Dagster. Consult the [GitHub repository for `kedro-dagster`](https://github.com/gtauzin/kedro-dagster) for further details, take a look at the [documentation](https://kedro-dagster.readthedocs.io/), or explore the GitHub repository for the associated example repository [`kedro-dagster-example`](https://github.com/gtauzin/kedro-dagster).
