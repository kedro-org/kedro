![Kedro logo](https://raw.githubusercontent.com/kedro-org/kedro/main/static/img/kedro_banner.png)

# Welcome to Kedro's award-winning documentation!

[![GitHub Actions - Main Branch](https://img.shields.io/github/actions/workflow/status/kedro-org/kedro/all-checks.yml?label=main)](https://github.com/kedro-org/kedro/actions/workflows/all-checks.yml?query=branch%3Amain)

[![GitHub Actions - Develop Branch](https://img.shields.io/github/actions/workflow/status/kedro-org/kedro/all-checks.yml?branch=develop&label=develop)](https://github.com/kedro-org/kedro/actions/workflows/all-checks.yml?query=branch%3Adevelop)

[![License is Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/license/apache2-0-php/)

[![Python version 3.9, 3.10, 3.11, 3.12, 3.13](https://img.shields.io/badge/3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/kedro/)

[![PyPI package version](https://badge.fury.io/py/kedro.svg)](https://pypi.org/project/kedro/)

[![Conda package version](https://img.shields.io/conda/vn/conda-forge/kedro.svg)](https://anaconda.org/conda-forge/kedro)

[![Docs build status](https://readthedocs.org/projects/kedro/badge/?version=stable)](https://docs.kedro.org/)

[![Kedro\'s Slack organisation](https://img.shields.io/badge/slack-chat-blueviolet.svg?label=Kedro%20Slack&logo=slack)](https://slack.kedro.org)

[![Kedro\'s Slack archive](https://img.shields.io/badge/slack-archive-blueviolet.svg?label=Kedro%20Slack%20)](https://linen-slack.kedro.org/)

[![Linted and Formatted with Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![OpenSSF Best Practices Badge Program](https://bestpractices.coreinfrastructure.org/projects/6711/badge)](https://bestpractices.coreinfrastructure.org/projects/6711)

## Getting started

- [Kedro architecture](pages/getting-started/architecture_overview.md)
- [Kedro's CLI](pages/getting-started/commands_reference.md)
<!-- - [Quickstart](pages/getting-started/quickstart.md) -->
- [Installation](pages/getting-started/install.md)
- [Glossary](pages/getting-started/glossary.md)

## Tutorials

- [Kedro Spaceflights tutorial](pages/tutorials/spaceflights_tutorial.md)
- [Kedro for Notebook tutorial](pages/tutorials/notebooks_tutorial.md)

## Create

- [Create a Kedro project](pages/create/new_project.md)
- [Create a minimal Kedro project](pages/create/minimal_kedro_project.md)
- [Customise a new project](pages/create/customise_project.md)
- [Kedro starters](pages/create/starters.md)

## Configure

- [Migration guide for config loaders](pages/configure/config_loader_migration.md)
- [Advanced configuration](pages/configure/advanced_configuration.md)
- [Parameters](pages/configure/parameters.md)
- [Credentials](pages/configure/credentials.md)

## Catalog Data

- [Introduction](pages/catalog-data/introduction.md)
- [Data Catalog YAML examples](pages/catalog-data/data_catalog_yaml_examples.md)
- [Dataset factories](pages/catalog-data/kedro_dataset_factories.md)
- [Data and pipeline versioning](pages/catalog-data/kedro_dvc_versioning.md)
- [Partitioned and incremental datasets](pages/catalog-data/partitioned_and_incremental_datasets.md)
- [Data Catalog test phase](pages/catalog-data/test_phase.md)

## Build

- [Nodes](pages/build/nodes.md)
- [Pipeline object](pages/build/pipeline_introduction.md)
- [Run a pipeline](pages/build/run_a_pipeline.md)
- [Modular pipelines](pages/build/modular_pipelines.md)
- [Reusing pipelines (namespaces)](pages/build/namespaces.md)
- [Pipeline registry](pages/build/pipeline_registry.md)
- [Slice a pipeline](pages/build/slice_a_pipeline.md)

## Develop

- [Logging](pages/develop/logging.md)
- [Automated testing](pages/develop/automated_testing.md)
- [Code formatting and linting](pages/develop/linting.md)
- [Debugging](pages/develop/debugging.md)

## Deploy

- [Single-machine deployment](pages/deploy/single_machine.md)
- [Distributed deployment](pages/deploy/distributed.md)
- Supported platforms:
  - [Apache Airflow](pages/deploy/supported-platforms/airflow.md)
  - [Amazon SageMaker](pages/deploy/supported-platforms/amazon_sagemaker.md)
  - [Amazon EMR Serverless](pages/deploy/supported-platforms/amazon_emr_serverless.md)
  - [AWS Step Functions](pages/deploy/supported-platforms/aws_step_functions.md)
  - [Azure ML pipelines](pages/deploy/supported-platforms/azure.md)
  - [Dask](pages/deploy/supported-platforms/dask.md)
  - [Kubeflow Pipelines](pages/deploy/supported-platforms/kubeflow.md)
  - [Prefect](pages/deploy/supported-platforms/prefect.md)
  - [VertexAI](pages/deploy/supported-platforms/vertexai.md)
  - [Argo Workflows](pages/deploy/supported-platforms/argo.md)
  - [AWS Batch](pages/deploy/supported-platforms/aws_batch.md)

## Extend

- [Use Cases](pages/extend/common_use_cases.md)
- [Custom datasets](pages/extend/how_to_create_a_custom_dataset.md)
- [Custom plugins](pages/extend/plugins.md)
- [Custom starters](pages/extend/create_a_starter.md)

## Reference

- [Kedro API](pages/api/index.md)
  - [kedro.config](pages/api/config/kedro.config.md)
  - [kedro.framework](pages/api/framework/kedro.framework.md)
  - [kedro.io](pages/api/io/kedro.io.md)
  - [kedro.ipython](pages/api/ipython/kedro.ipython.md)
  - [kedro.logging](pages/api/kedro.logging.md)
  - [kedro.pipeline](pages/api/pipeline/kedro.pipeline.md)
  - [kedro.runner](pages/api/runner/kedro.runner.md)
  - [kedro.utils](pages/api/kedro.utils.md)

## Integration & Plugins

- [PySpark](pages/integrations-and-plugins/pyspark_integration.md)
- [MLflow](pages/integrations-and-plugins/mlflow.md)
- [Delta Lake](pages/integrations-and-plugins/deltalake_versioning.md)
- [Iceberg](pages/integrations-and-plugins/iceberg_versioning.md)

## IDE Support

- [Visual Studio Code](pages/ide/set_up_vscode.md)
- [PyCharm](pages/ide/set_up_pycharm.md)

## About

- [Kedro's Technical Steering Committee](pages/about/technical_steering_committee.md)
- [Migration guide](pages/about/migration.md)
- [Kedro telemetry](pages/about/telemetry.md)
