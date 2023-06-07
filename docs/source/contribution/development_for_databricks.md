# Contribute changes to Kedro that are tested on Databricks

Many Kedro users deploy their projects to [Databricks](https://www.databricks.com/), a cloud-based platform for data engineering and data science. We encourage contributions to extend and improve the experience for Kedro users on Databricks; this guide explains how to efficiently test your locally modified version of Kedro on Databricks as part of a build-and-test development cycle.

## How to deploy a development version of Kedro to Databricks

```{note}
This page is for **contributors** developing changes to Kedro that need to test them on Databricks. If you are a Kedro user working on an individual or team project and need more information about workflows, consult the [documentation pages for developing a Kedro project on Databricks](../deployment/databricks/index.md).
```

## Prerequisites

You will need the following to follow this guide:

* Python **version >=3.8**.
* An activated Python virtual environment into which you have installed the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) with [authentication for your workspace](https://docs.databricks.com/dev-tools/cli/index.html#set-up-the-cli).
* Access to a Databricks workspace with an [existing cluster](https://docs.databricks.com/clusters/create-cluster.html).
* [GNU `make`](https://www.gnu.org/software/make/).
* [`git`](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).
* A local clone of the [Kedro git repository](https://github.com/kedro-org/kedro).

## How to install a build of Kedro onto Databricks

The development workflow for Kedro on Databricks is similar to the one for Kedro in general, when you develop and test your changes locally. The main difference comes when manually testing your changes on Databricks, since you will need to build and deploy the wheel file to Databricks to test it on a cluster.

To make developing Kedro for Databricks easier, Kedro comes with a `Makefile` target named `databricks-build` that automates the process of building a wheel file and installing this on your Databricks cluster to save development time.

### How to set up the Databricks CLI to test a Kedro build

Before you use `make databricks-build`, you must [set up the Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html#set-up-the-cli).

Next, create and environment variable with the ID of the cluster you are using to test your Kedro build. You can find the ID by executing the Databricks CLI command `databricks clusters list` and looking for the Cluster ID to the left of the name of your chosen cluster, for instance:

```bash
$ databricks clusters list
1234-567890-abcd1234  General Cluster             TERMINATED
0987-654321-9876xywz  Kedro Test Cluster          TERMINATED
```

In this case, the cluster ID of `Kedro Test Cluster` is `0987-654321-9876xywz`.

Once you have determined the cluster ID, you must export it to an environment variable named `DATABRICKS_CLUSTER_ID`:

```bash
# Linux or macOS
export DATABRICKS_CLUSTER_ID=<your-cluster-id>

# Windows (PowerShell)
$Env:DATABRICKS_CLUSTER_ID = '<your-cluster-id>'
```

### How to use `make databricks-build` to test your Kedro build

With the setup complete, you can use `make databricks-build`. In your terminal, navigate to the parent directory of your Kedro development repository and run:

```bash
make databricks-build
```

You should see a stream of messages being written to your terminal. Behind the scenes, `databricks-build` does the following:

1. Builds a wheel file of your modified version of Kedro.
2. Uninstalls any library on your Databricks cluster with the same wheel file name.
3. Uploads your updated wheel file to DBFS (Databricks File System).
4. Queues your updated wheel file for installation
5. Restarts your cluster to apply the changes.

Note that your cluster will be unavailable while it restarts. You can poll the status of the cluster using the Databricks CLI:

```bash
# Linux or macOS
databricks clusters get --cluster-id $DATABRICKS_CLUSTER_ID | grep state

# Windows (PowerShell)
databricks clusters get --cluster-id $Env:DATABRICKS_CLUSTER_ID | Select-String state
```

Once the cluster has restarted, you should verify that your modified version of Kedro has been correctly installed. Run `databricks libraries list --cluster-id <your-cluster-id>`. If installation was successful, you should see the following output:

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

Any runs of a Kedro project on this cluster will now reflect your latest local changes to Kedro. You can now test your changes to Kedro by using your cluster to run a Kedro project.
