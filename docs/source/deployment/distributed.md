# Distributed deployment
This topic explains how to deploy Kedro in a distributed system.

Distributed applications refer to software that runs on multiple computers within a network at the same time and can be stored on servers or with cloud computing. Unlike traditional applications that run on a single machine, distributed applications run on multiple systems simultaneously for a single task or job.

You may select to use a distributed system if your Kedro pipelines are very compute-intensive to benefit from the cloud's elasticity and scalability to manage compute resources.

As a distributed deployment strategy, we recommend the following series of steps:

## 1. Containerise the pipeline

For better dependency management, we encourage you to containerise the entire pipeline/project. We recommend using [Docker](https://www.docker.com/), but you're free to use any preferred container solution available to you. For the purpose of this walk-through, we are going to assume a `Docker` workflow.

Firstly make sure your [project requirements are up-to-date](../kedro_project_setup/dependencies.md) by running:

```bash
pip-compile --output-file=<project_root>/requirements.txt --input-file=<project_root>/requirements.txt
```

We then recommend the [`Kedro-Docker`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin to streamline the process of building the image. [Instructions for using this are in the plugin's README.md](https://github.com/kedro-org/kedro-plugins/blob/main/README.md).


After you’ve built the Docker image for your project locally, you would typically have to transfer the image to a container registry, such as DockerHub or AWS Elastic Container Registry, to be able to pull it on your remote servers. You can find instructions on how to do so [in our guide for single-machine deployment](./single_machine.md#how-to-use-container-registry).

## 2. Convert your Kedro pipeline into targeted platform primitives

A Kedro pipeline benefits from a structure that's normally easy to translate (at least semantically) into the language that different platforms would understand. A DAG of `nodes` can be converted into a series of tasks where each node maps to an individual task, whether it being a Kubeflow operator, an AWS Batch job, etc, and the dependencies are the same as those mapped in `Pipeline.node_dependencies`.

To perform the conversion programmatically, you will need to develop a script. Make sure you save all your catalog entries to a remote location and that you make best use of node `names` as `tags` in your pipeline to simplify the process. For example, you should name all nodes, and use a programmer-friendly naming convention.

## 3. Parameterise the runs

A `node` typically corresponds to a unit of compute, which can be run by parameterising the basic `kedro run`:

 ```bash
kedro run --node=<node_name>
```

We encourage you to play with different ways of parameterising your runs as you see fit. Use names, tags, custom flags, in preference to making a code change to execute different behaviour. All your jobs/tasks/operators/etc. should have the same version of the code, i.e. same Docker image, to run on.

## 4. (Optional) Create starters

This is an optional step, but it may speed up your work in the long term. If you find yourself having to deploy in a similar environment or to a similar platform fairly often, you may want to [build your own Kedro starter](../kedro_project_setup/starters.md). That way you will be able to re-use any deployment scripts written as part of step 2.
