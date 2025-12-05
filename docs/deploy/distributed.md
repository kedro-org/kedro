# Distributed deployment
This topic explains how to deploy Kedro in a distributed system.

Distributed applications refer to software that runs on multiple computers within a network at the same time and can be stored on servers or with cloud computing. Unlike traditional applications that run on a single machine, distributed applications run on multiple systems simultaneously for a single task or job.

You may select a distributed system if your Kedro pipelines require significant compute so you can benefit from the cloud's elasticity and scalability.

As a distributed deployment strategy, we recommend the following series of steps:

## 1. Containerise the pipeline

For better dependency management, we encourage you to containerise the entire pipeline or project. We recommend using [Docker](https://www.docker.com/), but you're free to use any preferred container solution available to you. For this walk-through, we assume a Docker workflow.

Firstly make sure your [project requirements are up-to-date](../develop/dependencies.md) by running:

```bash
pip-compile --output-file=<project_root>/requirements.txt --input-file=<project_root>/requirements.txt
```

We recommend the [`kedro-docker`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin to streamline the process of building the image. [Instructions for using this are in the plugin README](https://github.com/kedro-org/kedro-plugins/blob/main/README.md).


After you build the Docker image for your project locally, transfer the image to a container registry, such as Docker Hub or AWS Elastic Container Registry, so you can pull it on your remote servers. You can find instructions on how to do so [in our guide for single-machine deployment](./single_machine.md#how-to-use-container-registry).

## 2. Convert your Kedro pipeline into targeted platform primitives

A Kedro pipeline benefits from a structure that is straightforward to translate (at least semantically) into the language that different platforms understand. A DAG of `nodes` can be converted into a series of tasks where each node maps to an individual task, whether it is a Kubeflow operator, an AWS Batch job, or another platform-specific primitive, and the dependencies match those mapped in `Pipeline.node_dependencies`.

To perform the conversion programmatically, you will need to develop a script. Make sure you save all your catalog entries to a remote location and that you make best use of node `names` as `tags` in your pipeline to simplify the process. For example, you should name all nodes, and use a programmer-friendly naming convention.

## 3. Parameterise the runs

A `node` typically corresponds to a unit of compute, which can be run by parameterising the basic `kedro run`:

```bash
kedro run --nodes=<node_name>
```

We encourage you to experiment with different ways of parameterising your runs. Use names, tags, and custom flags in preference to making a code change to execute different behaviour. All your jobs, tasks, and operators should have the same version of the code, that is, the same Docker image.

## 4. (Optional) Create starters

You may opt to [build your own Kedro starter](../tutorials/settings.md) if you often have to deploy in a similar environment or to a similar platform. The starter enables you to reuse any deployment scripts written as part of step 2.
