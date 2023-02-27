# Setup for developing and extending Kedro on Databricks

[Databricks](https://www.databricks.com/) is a cloud-based platform for data engineering and data science that many Kedro users deploy their Kedro projects to. As such, extending and improving the Kedro experience on Databricks is important to a large part of Kedro's user base. 

This page explains how to set up your development environment for Kedro on Databricks so that you can manually test the code you write as part a build-and-test cycle.

## Introduction

This guide describes:

1. How to build and deploy a modified version of Kedro (or a Kedro Dataset) on Databricks.
2. How to run your Kedro build on a pipeline.

## Prerequisites

You will need the following prerequisites to follow this guide:

1. GNU `make` installed.
2. Access to a Databricks workspace.
3. [`git` installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).
4. [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) installed and configured.
5. [Databricks `dbx`](https://docs.databricks.com/dev-tools/dbx.html#requirements) CLI installed.
6. A local clone of the Kedro (or Kedro Datasets) repository.

## Building Kedro on Databricks

The development workflow for Kedro on Databricks is similar to the one for Kedro in general. The main difference comes when manually testing your changes on Databricks. You can develop and test your changes locally, but you will need to build and deploy the wheel file to Databricks to test it on a cluster.

To make developing Kedro for Databricks easier, Kedro comes with a tool that automates the process of building a wheel file and deploying this to your databricks cluster. In order to use it, you will need to set up a few environment variables:

```bash
export DATABRICKS_CLUSTER_ID=<your-cluster-id>
export DATABRICKS_HOST=<your-databricks-host>
export DATABRICKS_TOKEN=<your-databricks-token>
```

To find your cluster ID, navigate to the Databricks workspace and then to the cluster you want to test on (under the 'Compute' tab). The cluster ID is the last part of the URL, after `/#setting/clusters/`.


### Using `make databricks-build`

 To use it, navigate to the Kedro repository and use `make`:

```bash
make databricks-build
```

Behind the scenes, this make target does the following:

1. Builds a wheel file of your modified version of Kedro.
2. Uninstalls any library on your Databricks cluster with the same wheel file name.
3. Uploads your updated wheel file to DBFS (Databricks File System).
4. Queues your updated wheel file for installation
5. Restarts your cluster to apply the changes.

Note that your cluster will be unavailable while it is restarting.

## Running Kedro on Databricks

