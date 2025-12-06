# AWS Batch (outdated documentation that needs review)

!!! warning
    This page contains outdated documentation that has not been tested against recent Kedro releases. If you manage to use AWS Batch with a recent version of Kedro, consider telling us the steps you took on [Slack](https://slack.kedro.org) or [GitHub](https://github.com/kedro-org/kedro/issues).

## Why use AWS Batch
[AWS Batch](https://aws.amazon.com/batch/) is optimised for batch computing and applications that scale with the number of jobs running in parallel. It manages job execution and compute resources, and dynamically provisions the optimal quantity and type. AWS Batch can assist with planning, scheduling, and executing your batch computing workloads, using [Amazon EC2](https://aws.amazon.com/ec2/) On-Demand and [Spot Instances](https://aws.amazon.com/ec2/spot/), and it has native integration with [CloudWatch](https://aws.amazon.com/cloudwatch/) for log collection.

AWS Batch helps you run massively parallel Kedro pipelines in a cost-effective way. It also allows you to parallelise the pipeline execution across multiple compute instances. Each Batch job is run in an isolated Docker container environment.

The following sections are a guide on how to deploy a Kedro project to AWS Batch, and uses the [spaceflights tutorial](../../tutorials/spaceflights_tutorial.md) as primary example. The guide assumes that you have already completed the tutorial, and that the project was created with the project name **Kedro Tutorial**.

## Prerequisites

To use AWS Batch, ensure you have the following prerequisites in place:

- An [AWS account set up](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/).
- A `name` attribute is set for each Kedro [Node][kedro.pipeline.node]. Each node will run in its own Batch job, so having sensible node names will make it easier to `kedro run --nodes=<node_name>`.
- [All node input/output datasets must be configured in `catalog.yml`](../../catalog-data/data_catalog_yaml_examples.md) and point to an external location (for example, AWS S3). A clean way to do this is to create a new configuration environment `conf/aws_batch` containing a `catalog.yml` file with the appropriate configuration, as illustrated below.

??? example "View code"
    ```yaml
    companies:
    type: pandas.CSVDataset
    filepath: s3://<your-bucket>/companies.csv

    reviews:
    type: pandas.CSVDataset
    filepath: s3://<your-bucket>/reviews.csv

    shuttles:
    type: pandas.ExcelDataset
    filepath: s3://<your-bucket>/shuttles.xlsx

    preprocessed_companies:
    type: pandas.CSVDataset
    filepath: s3://<your-bucket>/preprocessed_companies.csv

    preprocessed_shuttles:
    type: pandas.CSVDataset
    filepath: s3://<your-bucket>/preprocessed_shuttles.csv

    model_input_table:
    type: pandas.CSVDataset
    filepath: s3://<your-bucket>/model_input_table.csv

    regressor:
    type: pickle.PickleDataset
    filepath: s3://<your-bucket>/regressor.pickle
    versioned: true

    X_train:
    type: pickle.PickleDataset
    filepath: s3://<your-bucket>/X_train.pickle

    X_test:
    type: pickle.PickleDataset
    filepath: s3://<your-bucket>/X_test.pickle

    y_train:
    type: pickle.PickleDataset
    filepath: s3://<your-bucket>/y_train.pickle

    y_test:
    type: pickle.PickleDataset
    filepath: s3://<your-bucket>/y_test.pickle
    ```

## Run a Kedro pipeline with  AWS Batch

### Containerise your Kedro project

Containerise your Kedro project with a preferred container solution (for example, [Docker](https://www.docker.com/)) to build an image for AWS Batch.

This walk-through assumes a Docker workflow. Use the [Kedro-Docker plugin](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) to streamline the build. [Instructions are in the plugin README](https://github.com/kedro-org/kedro-plugins/blob/main/README.md).

After you build the Docker image locally, [transfer the image to a container registry](../single_machine.md#how-to-use-container-registry), such as [AWS ECR](https://aws.amazon.com/ecr/). You can follow Amazon's [ECR documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html) or open the repository in the [ECR dashboard](https://console.aws.amazon.com/ecr) and click `View push commands` for tailored steps.

### Provision resources

Provision the following resources before deploying your pipeline to AWS Batch:

#### Create the IAM role

If you store datasets in S3, create an IAM role so Batch can read and write to the relevant locations. Follow the AWS tutorial on [creating a fetch and run job](https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/) and set the policy in step 3 to `AmazonS3FullAccess`. Name the role `batchJobRole`.

#### Create AWS Batch job definition

Job definitions specify the resources needed to run a job. Create a job definition named `kedro_run`, assign it the `batchJobRole` IAM role, select the container image you built earlier, set the execution timeout to 300 seconds, and allocate 2000 MB of memory. Leave `Command` blank and keep the defaults.

#### Create AWS Batch compute environment

Create a managed, on-demand compute environment named `spaceflights_env`. Let AWS create service and instance roles if none exist. A managed environment lets AWS scale instances automatically.

!!! note
    The compute environment does not contain instances until you trigger the pipeline run, so creating it does not incur immediate cost.

#### Create AWS Batch job queue

A job queue is the bridge between the submitted jobs and the compute environment they should run on. Create a queue named `spaceflights_queue`, connected to your newly created compute environment `spaceflights_env`, and give it `Priority` 1.

### Configure the credentials

Ensure you have AWS credentials configured so the pipeline can access the relevant services. See the [AWS CLI documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) for setup instructions.

!!! note
    Configure the default region to match the region where you created the Batch resources.

### Submit AWS Batch jobs

With the resources in place, submit jobs to Batch programmatically by using the job definition and queue. Each job runs one node. To keep the correct execution order, specify the dependencies (job IDs) of each submitted job. You can use a custom runner for this step.

#### Create a custom runner

Create a new Python package `runner` in your `src` folder (for example, `kedro_tutorial/src/kedro_tutorial/runner/`). Make sure there is an `__init__.py` file at this location, and add another file named `batch_runner.py`, which will contain the implementation of your custom runner, `AWSBatchRunner`. The `AWSBatchRunner` will submit and track jobs asynchronously, surfacing any errors that occur on Batch.

Make sure the `__init__.py` file in the `runner` folder includes the following import and declaration:

```python
from .batch_runner import AWSBatchRunner

__all__ = ["AWSBatchRunner"]
```

Copy the contents of the script below into `batch_runner.py`:

```python
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from typing import Any, Dict, Set

import boto3

from kedro.io import DataCatalog
from kedro.pipeline.pipeline import Pipeline, Node
from kedro.runner import ThreadRunner


class AWSBatchRunner(ThreadRunner):
    def __init__(
        self,
        max_workers: int = None,
        job_queue: str = None,
        job_definition: str = None,
        is_async: bool = False,
    ):
        super().__init__(max_workers, is_async=is_async)
        self._job_queue = job_queue
        self._job_definition = job_definition
        self._client = boto3.client("batch")

    def create_default_dataset(self, ds_name: str):
        raise NotImplementedError("All datasets must be defined in the catalog")

    def _get_required_workers_count(self, pipeline: Pipeline):
        if self._max_workers is not None:
            return self._max_workers

        return super()._get_required_workers_count(pipeline)

    def _run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager,
        run_id: str = None,
    ) -> None:
        nodes = pipeline.nodes
        node_dependencies = pipeline.node_dependencies
        todo_nodes = set(node_dependencies.keys())
        node_to_job = dict()
        done_nodes = set()  # type: Set[Node]
        futures = set()
        max_workers = self._get_required_workers_count(pipeline)

        self._logger.info("Max workers: %d", max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            while True:
                # Process the nodes that have completed, meaning jobs that reached
                # FAILED or SUCCEEDED state
                done = {fut for fut in futures if fut.done()}
                futures -= done
                for future in done:
                    try:
                        node = future.result()
                    except Exception:
                        self._suggest_resume_scenario(pipeline, done_nodes)
                        raise
                    done_nodes.add(node)
                    self._logger.info(
                        "Completed %d out of %d jobs", len(done_nodes), len(nodes)
                    )

                # A node is ready to be run if all its upstream dependencies have been
                # submitted to Batch, meaning all node dependencies were assigned a job ID
                ready = {
                    n for n in todo_nodes if node_dependencies[n] <= node_to_job.keys()
                }
                todo_nodes -= ready
                # Asynchronously submit Batch jobs
                for node in ready:
                    future = pool.submit(
                        self._submit_job,
                        node,
                        node_to_job,
                        node_dependencies[node],
                        run_id,
                    )
                    futures.add(future)

                # If no more nodes left to run, ensure the entire pipeline was run
                if not futures:
                    assert not todo_nodes, (todo_nodes, done_nodes, ready, done)
                    break
```

Next you will want to add the implementation of the `_submit_job()` method referenced in `_run()`. This method will create and submit jobs to AWS Batch with the following:

* Correctly specified upstream dependencies
* A unique job name
* The corresponding command to run, namely `kedro run --nodes=<node_name>`.

Once submitted, the method tracks progress and surfaces any errors if the jobs end in `FAILED` state.

Make sure the contents below are placed inside the `AWSBatchRunner` class:

```python
def _submit_job(
    self,
    node: Node,
    node_to_job: Dict[Node, str],
    node_dependencies: Set[Node],
    run_id: str,
) -> Node:
    self._logger.info("Submitting the job for node: %s", str(node))

    job_name = f"kedro_{run_id}_{node.name}".replace(".", "-")
    depends_on = [{"jobId": node_to_job[dep]} for dep in node_dependencies]
    command = ["kedro", "run", "--nodes", node.name]

    response = self._client.submit_job(
        jobName=job_name,
        jobQueue=self._job_queue,
        jobDefinition=self._job_definition,
        dependsOn=depends_on,
        containerOverrides={"command": command},
    )

    job_id = response["jobId"]
    node_to_job[node] = job_id

    _track_batch_job(job_id, self._client)  # make sure the job finishes

    return node
```

The last part of the implementation is the helper function `_track_batch_job()`, called from `_submit_job()`, which looks like this:

```python
def _track_batch_job(job_id: str, client: Any) -> None:
    """Continuously poll the Batch client for a job's status,
    given the job ID. If it ends in FAILED state, raise an exception
    and log the reason. Return if successful.
    """
    while True:
        # we don't want to bombard AWS with the requests
        # to not get throttled
        sleep(1.0)

        jobs = client.describe_jobs(jobs=[job_id])["jobs"]
        if not jobs:
            raise ValueError(f"Job ID {job_id} not found.")

        job = jobs[0]
        status = job["status"]

        if status == "FAILED":
            reason = job["statusReason"]
            raise Exception(
                f"Job {job_id} has failed with the following reason: {reason}"
            )

        if status == "SUCCEEDED":
            return
```

#### Set up Batch-related configuration

You'll need to set the Batch-related configuration that the runner will use. Add a `parameters.yml` file inside the `conf/aws_batch/` directory created as part of the prerequisites with the following keys:

```yaml
aws_batch:
  job_queue: "spaceflights_queue"
  job_definition: "kedro_run"
  max_workers: 2
```

#### Update CLI implementation

You're nearly there! Before you can use the new runner, add a `cli.py` file at the same level as `settings.py`, using [the template we provide](../../getting-started/commands_reference.md#customise-or-override-project-specific-kedro-commands). Update the `run()` function in the new `cli.py` file so that the runner class is instantiated with the right configuration:

```python
def run(tag, env, ...):
    """Run the pipeline."""
    runner = runner or "SequentialRunner"

    tag = _get_values_as_tuple(tag) if tag else tag
    node_names = _get_values_as_tuple(node_names) if node_names else node_names

    with KedroSession.create(env=env, extra_params=params) as session:
        context = session.load_context()
        runner_instance = _instantiate_runner(runner, is_async, context)
        session.run(
            tags=tag,
            runner=runner_instance,
            node_names=node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_version,
            pipeline_name=pipeline,
        )
```

where the helper function `_instantiate_runner()` looks like this:

```python
def _instantiate_runner(runner, is_async, project_context):
    runner_class = load_obj(runner, "kedro.runner")
    runner_kwargs = dict(is_async=is_async)

    if runner.endswith("AWSBatchRunner"):
        batch_kwargs = project_context.params.get("aws_batch") or {}
        runner_kwargs.update(batch_kwargs)

    return runner_class(**runner_kwargs)
```

### Deploy

You're now ready to trigger the run. Execute the following command:

```bash
kedro run --env=aws_batch --runner=kedro_tutorial.runner.AWSBatchRunner
```

You should start seeing jobs appearing on your Jobs dashboard, under the `Runnable` tab - meaning they're ready to start as soon as the resources are provisioned in the compute environment.

AWS Batch has native integration with CloudWatch, where you can check the logs for a particular job. You can either click on [the Batch job in the Jobs tab](https://console.aws.amazon.com/batch/home/jobs) and click `View logs` in the pop-up panel, or go to [CloudWatch dashboard](https://console.aws.amazon.com/cloudwatch), click `Log groups` in the side bar and find `/aws/batch/job`.
