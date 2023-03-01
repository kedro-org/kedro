# How to deploy a development version of Kedro to Databricks

[Databricks](https://www.databricks.com/) is a cloud-based platform for data engineering and data science that many Kedro users deploy their Kedro projects to. Extending and improving the Kedro experience on Databricks is important to a large part of Kedro's user base.

## Introduction

This page describes how to efficiently develop features and fixes for Kedro on Databricks. Using this guide, you will be able to quickly test your locally modified version of Kedro on Databricks as part of a build-and-test development cycle.

## Prerequisites

You will need the following prerequisites to follow this guide:

1. Python **version >=3.8** installed.
2. A Python virtual environment activated in which the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) is installed with [authentication for your workspace](https://docs.databricks.com/dev-tools/cli/index.html#set-up-the-cli).
3. Access to a Databricks workspace with an [existing cluster](https://docs.databricks.com/clusters/create-cluster.html).
4. [GNU `make`](https://www.gnu.org/software/make/) installed.
5. [`git` installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).
6. A local clone of the [Kedro](https://github.com/kedro-org/kedro) repository for you to edit.

## How to install a build of Kedro onto Databricks

The development workflow for Kedro on Databricks is similar to the one for Kedro in general, when you develop and test your changes locally. The main difference comes when manually testing your changes on Databricks, since you will need to build and deploy the wheel file to Databricks to test it on a cluster.

To make developing Kedro for Databricks easier, Kedro comes with a `Makefile` target named `databricks-build` that automates the process of building a wheel file and installing this on your Databricks cluster to save development time.

### Setup the Databricks CLI to test a Kedro build

In order to use `databricks-build`, you must have completed the [setup of the Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html#set-up-the-cli).

The only remaining step is to create and environment variable with the ID of the cluster you are using to test your Kedro build. You can find the ID by executing the Databricks CLI command `databricks cluster list` and looking for the name of your chosen cluster.

Once you have found the cluster ID, you must export it to an environment variable named `DATABRICKS_CLUSTER_ID`, on Linux or macOS:

```bash
export DATABRICKS_CLUSTER_ID=<your-cluster-id>
```

### Using `make databricks-build`

With the setup complete, you can use `databricks-build`. Navigate to the parent directory of your Kedro development repository and run:

```bash
make databricks-build
```

You should see a stream of messages being written to your terminal. Behind the scenes, `build-databricks` does the following:

1. Builds a wheel file of your modified version of Kedro.
2. Uninstalls any library on your Databricks cluster with the same wheel file name.
3. Uploads your updated wheel file to DBFS (Databricks File System).
4. Queues your updated wheel file for installation
5. Restarts your cluster to apply the changes.

Note that your cluster will be unavailable while it is restarting. You can poll the status of your cluster using the Databricks CLI command `databricks clusters get --cluster-id <your-cluster-id> | grep state` (macOS, Linux).

After waiting for your cluster to restart, you should verify that your modified version of Kedro has installed correctly. To do this, run `databricks libraries list --cluster-id <your-cluster-id>`. If installation was successful, you should see the following output:

```bash
{
  "cluster_id": "<your-cluster-id>",
  "library_statuses": [
    {
      "library": {
        "whl": "dbfs:/tmp/kedro-builds/kedro-<version>-py3-none-any.whl"
      },
      "status": "INSTALLED",
      "is_library_for_all_clusters": false
    }
  ]
}
```

Any runs of a Kedro project on this cluster will now reflect your latest local changes to Kedro.
