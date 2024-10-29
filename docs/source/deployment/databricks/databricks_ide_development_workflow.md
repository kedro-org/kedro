# Use Databricks Asset Bundles to deploy a Kedro project

```{note}
The `dbx` package is deprecated by Databricks, and dbx workflow documentation is moved to a [new page](./databricks_dbx_workflow.md).
```

This guide demonstrates a wokrflow for developing Kedro Project on Databricks using Databricks Asset Bundles. You will learn how to develop your project using local environment, then use `kedro-databricks` and Databricks Asset Bundle `to package your code for running pipeline on Databricks.

By working in your local environment, you can take advantage of features within an IDE that are not available on Databricks notebooks:

- Auto-completion and suggestions for code, improving your development speed and accuracy.
- Linters like [Ruff](https://docs.astral.sh/ruff) can be integrated to catch potential issues in your code.
- Static type checkers like Mypy can check types in your code, helping to identify potential type-related issues early in the development process.

To set up these features, look for instructions specific to your IDE (for instance, [VS Code](https://code.visualstudio.com/docs/python/linting)).

If you prefer to develop projects in notebooks rather than in an IDE, you should follow our guide on [how to develop a Kedro project within a Databricks workspace](./databricks_notebooks_development_workflow.md) instead.



## What this page covers

The main steps in this tutorial are as follows:

- [Use Databricks Asset Bundles to deploy a Kedro project](#use-databricks-asset-bundles-to-deploy-a-kedro-project)
  - [What this page covers](#what-this-page-covers)
  - [Prerequisites](#prerequisites)
  - [Set up your project](#set-up-your-project)
    - [Note your Databricks username and host](#note-your-databricks-username-and-host)
    - [Install Kedro and databricks CLI in a new virtual environment](#install-kedro-and-databricks-cli-in-a-new-virtual-environment)
    - [Authenticate the Databricks CLI](#authenticate-the-databricks-cli)
    - [Create a new Kedro Project](#create-a-new-kedro-project)
    - [Create the Datanrickls Asset Bundles using `kedro-databricks`](#create-the-datanrickls-asset-bundles-using-kedro-databricks)
    - [Deploy Databricks Job using Databricks Asset Bundles](#deploy-databricks-job-using-databricks-asset-bundles)
    - [Run Databricks Job with `databricks` CLI](#run-databricks-job-with-databricks-cli)

## Prerequisites

- An active [Databricks deployment](https://docs.databricks.com/getting-started/index.html).
- A [Databricks cluster](https://docs.databricks.com/clusters/configure.html) configured with a recent version (>= 11.3 is recommended) of the Databricks runtime.
- [Conda installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine in order to create a virtual environment with a specific version of Python (>= 3.9 is required). If you have Python >= 3.9 installed, you can use other software to create a virtual environment.

## Set up your project
### Note your Databricks username and host
### Install Kedro and databricks CLI in a new virtual environment

### Authenticate the Databricks CLI
### Create a new Kedro Project
### Create the Databricks Asset Bundles using `kedro-databricks`
`kedro-databricks` is a wrapper around `databricks` CLI. It is the simplest way to get started without getting stuck with configuration. To find more about Databricks Asset Bundles, customisation, you can read [What are Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html)

Install `kedro-databricks` with:
`pip install kedro-databricks`
Then run this command:
`kedro databricks init`

This will generate a `databricks.yml` sitting inside the `conf` folder. By default it sets the resource, i.e. cluster type you need. Optionally, you can override these configurations. 

To create Databricks Asset Bundles, run:
`kedro databricks bundle`

If `conf/databricks.yml` exist, it will read the configuration and override the corresponding keys. This generates the Databricks job configuration inside a `resource` folder. 

### Deploy Databricks Job using Databricks Asset Bundles
Once you have all the resource generated, run this command to deploy Databriks Asset Bundles to Databricks:
`kedro databricks deploy`

You should see something similar:
> Uploading databrick_iris-0.1-py3-none-any.whl...
> Uploading bundle files to /Workspace/Users/xxxxxxx.com/.bundle/databrick_iris/local/files...
> Deploying resources...
> Updating deployment state...
> Deployment complete!

Once you see the `Deployment complete` log, you can now run your pipelines on Databricks!

#### How to run the Deployed job?
There are two options to run Databricks Jobs:
1. Use the `databricks` CLI
2. Use Databricks UI
#### Run Databricks Job with `databricks` CLI
`databricks bundle run`


#### Run Databricks Job with Databricks UI
[add images later]