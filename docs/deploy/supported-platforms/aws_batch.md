# AWS Batch

## Why use AWS Batch

[AWS Batch](https://aws.amazon.com/batch/) is optimised for batch computing and applications that scale with the number of jobs running in parallel. It manages job execution and compute resources, and dynamically provisions the optimal quantity and type. AWS Batch can assist with planning, scheduling, and executing your batch computing workloads using [Amazon EC2](https://aws.amazon.com/ec2/) On-Demand and [Spot Instances](https://aws.amazon.com/ec2/spot/), and it has native integration with [CloudWatch](https://aws.amazon.com/cloudwatch/) for log collection.

AWS Batch helps you run Kedro pipelines in a cost-effective way by mapping each **namespace group** to an isolated Batch job. Namespace groups that have no dependencies between them can run in parallel; groups that produce outputs consumed by others run in sequence, with AWS Batch managing that ordering via its native `dependsOn` mechanism. Each Batch job runs in an isolated Docker container environment and executes all nodes within the namespace using Kedro's built-in runner, so intermediate datasets within a namespace can stay in memory and don't have to be saved to S3.

The following sections guide you through deploying a Kedro project to AWS Batch, using the [spaceflights tutorial](../../tutorials/spaceflights_tutorial.md) as the primary example. The guide assumes that you have completed the tutorial and that the project was created with the project name **Kedro Tutorial**.

## Prerequisites

To use AWS Batch, ensure you have the following prerequisites in place:

- An [AWS account set up](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/).
- Your project uses [namespaced pipelines](../../build/namespaces.md). Nodes must be organised into namespaces using the `Pipeline()` function so that each namespace can be dispatched as an independent Batch job.
- A `name` attribute set for each Kedro [Node][kedro.pipeline.node]. Node names appear in resume suggestions when a run fails partially.
- Only datasets that **cross namespace boundaries** must be configured in `catalog.yml` and point to an external location (for example, AWS S3). Datasets used entirely within a single namespace are resolved as in-memory datasets inside the Batch job and do not need catalog entries.

Create a configuration environment `conf/aws_batch` containing a `catalog.yml` file for the cross-namespace datasets. For spaceflights, the `data_processing` namespace outputs `model_input_table` which is consumed by the `data_science` namespace, so only that boundary dataset (plus raw inputs and the final model artefact) needs an S3 entry.

??? example "View catalog"
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

    # Cross-namespace: produced by data_processing, consumed by data_science
    model_input_table:
      type: pandas.CSVDataset
      filepath: s3://<your-bucket>/model_input_table.csv

    # Final model artefact
    data_science.regressor:
      type: pickle.PickleDataset
      filepath: s3://<your-bucket>/regressor.pickle
      versioned: true
    ```

    Internal datasets such as `data_processing.preprocessed_companies` and `data_processing.preprocessed_shuttles` are not listed here because they are produced and consumed within the `data_processing` namespace job and can remain in memory.


## Run a Kedro pipeline with AWS Batch

### Containerise your Kedro project

Containerise your Kedro project with a preferred container solution (for example, [Docker](https://www.docker.com/)) to build an image for AWS Batch.

This walk-through assumes a Docker workflow. Use the [Kedro-Docker plugin](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) to streamline the build. [Instructions are in the plugin README](https://github.com/kedro-org/kedro-plugins/blob/main/kedro-docker/README.md).

After you build the Docker image locally, [transfer the image to a container registry](../single_machine.md#how-to-use-container-registry), such as [AWS ECR](https://aws.amazon.com/ecr/). You can follow Amazon's [ECR documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html) or open the repository in the [ECR dashboard](https://console.aws.amazon.com/ecr) and click `View push commands` for tailored steps.

### Provision resources

Provision the following resources before deploying your pipeline to AWS Batch:

#### Create the IAM roles

Two IAM roles are required:

1. **ECS task execution role** — allows AWS Batch and ECS to pull the container image from ECR and write logs to CloudWatch. When creating the job definition in the AWS console, the wizard can create this role automatically if one does not already exist. If you create it manually, attach the `AmazonECSTaskExecutionRolePolicy` managed policy.

2. **Job role** (`batchJobRole`) — grants the container access to your data. If you store datasets in S3, create an IAM role and attach the `AmazonS3FullAccess` policy (or a scoped-down policy following least-privilege). This role is specified on the job definition as the **job role**, not the execution role.

#### Create AWS Batch job definition

Job definitions specify the resources needed to run a job. Create a job definition named `kedro_run`:

- **Container image**: select the ECR image you built earlier.
- **Job role**: assign `batchJobRole`.
- **Execution role**: assign the ECS task execution role.
- **Resource requirements**: set memory and vCPU using the `resourceRequirements` format. The old `memory` and `vCPUs` fields on the container properties are deprecated; use the resource requirements section in the console or the following structure in the API:

    ```json
    [
      {"type": "MEMORY", "value": "2000"},
      {"type": "VCPU", "value": "1"}
    ]
    ```

- **Command**: leave blank. The runner overrides the command at submission time.
- **Execution timeout**: set to a value that covers your longest-running namespace group.

!!! note "EC2 is required"
    This deployment approach uses `containerOverrides.command` to pass a `kedro run` command to each job. This override is supported on **EC2-backed compute environments only**. Fargate does not support command overrides at submission time and is therefore not compatible with this runner.

#### Create AWS Batch compute environment

Create a managed, on-demand EC2 compute environment named `spaceflights_env`. Let AWS create the service and instance roles if none exist. A managed environment lets AWS scale instances automatically.

!!! note
    The compute environment contains no instances until you trigger the pipeline run, so creating it does not incur immediate cost.

#### Create AWS Batch job queue

A job queue bridges submitted jobs and the compute environment they run on. Create a queue named `spaceflights_queue`, connected to `spaceflights_env`, with `Priority` 1.

### Configure the credentials

Ensure you have AWS credentials configured so the pipeline can access the relevant services. See the [AWS CLI documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) for setup instructions.

!!! note
    Configure the default region to match the region where you created the Batch resources.

### Submit AWS Batch jobs

With the resources in place, the `AWSBatchRunner` submits one Batch job per namespace group. It uses [`pipeline.group_nodes_by(group_by="namespace")`][kedro.pipeline.Pipeline.group_nodes_by] to determine the groups and their dependencies, submits all jobs upfront (AWS Batch handles the wait via `dependsOn`), and then tracks completion in parallel — surfacing any errors that occur.

#### Create a custom runner

Create a new Python package `runner` inside your `src` folder (for example, `src/kedro_tutorial/runner/`). Add an `__init__.py` file:

```python
from .batch_runner import AWSBatchRunner

__all__ = ["AWSBatchRunner"]
```

Add a `batch_runner.py` file with the following content:

```python
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from typing import TYPE_CHECKING, Any

import boto3

from kedro.pipeline import GroupedNodes, Pipeline
from kedro.runner import ThreadRunner


if TYPE_CHECKING:
    from pluggy import PluginManager

    from kedro.io import CatalogProtocol


class AWSBatchRunner(ThreadRunner):
    def __init__(
        self,
        max_workers: int | None = None,
        job_queue: str | None = None,
        job_definition: str | None = None,
        pipeline_name: str = "__default__",
        env: str | None = None,
        is_async: bool = False,
    ):
        super().__init__(max_workers=max_workers, is_async=is_async)
        self._job_queue = job_queue
        self._job_definition = job_definition
        self._pipeline_name = pipeline_name
        self._env = env
        self._client = boto3.client("batch")

    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluginManager | None = None,
        run_id: str | None = None,
    ) -> None:
        groups = pipeline.group_nodes_by(group_by="namespace")
        group_to_job: dict[str, str] = {}

        # Submit all jobs in dependency order.
        # group_nodes_by returns groups in topological order, so by the time
        # group A is processed all groups A depends on already have job IDs.
        for group in groups:
            depends_on = [
                {"jobId": group_to_job[dep]}
                for dep in group.dependencies
                if dep in group_to_job
            ]
            job_id = self._submit_group(group, depends_on, run_id)
            group_to_job[group.name] = job_id

        # Track all submitted jobs in parallel.
        done_groups: set[str] = set()
        nodes_by_group = {g.name: g.nodes for g in groups}
        node_objects = {n.name: n for n in pipeline.nodes}

        with ThreadPoolExecutor(max_workers=len(group_to_job) or 1) as pool:
            futures = {
                pool.submit(_track_batch_job, job_id, self._client): group_name
                for group_name, job_id in group_to_job.items()
            }
            for future in as_completed(futures):
                group_name = futures[future]
                try:
                    future.result()
                    done_groups.add(group_name)
                    self._logger.info(
                        "Completed group '%s' (%d/%d)",
                        group_name,
                        len(done_groups),
                        len(groups),
                    )
                except Exception:
                    done_nodes = {
                        node_objects[n]
                        for g in done_groups
                        for n in nodes_by_group[g]
                    }
                    self._suggest_resume_scenario(pipeline, done_nodes, catalog)
                    raise

    def _submit_group(
        self,
        group: GroupedNodes,
        depends_on: list[dict[str, str]],
        run_id: str | None,
    ) -> str:
        self._logger.info("Submitting job for group: %s", group.name)
        job_name = f"kedro_{run_id}_{group.name}".replace(".", "-")

        command = ["kedro", "run"]
        if self._env:
            command += ["--env", self._env]
        command += ["--pipelines", self._pipeline_name]
        if group.type == "namespace":
            command += ["--namespaces", group.name]
        else:
            command += ["--nodes", group.name]

        response = self._client.submit_job(
            jobName=job_name,
            jobQueue=self._job_queue,
            jobDefinition=self._job_definition,
            dependsOn=depends_on,
            containerOverrides={"command": command},
        )
        job_id = response["jobId"]
        self._logger.info("Submitted job %s for group: %s", job_id, group.name)
        return job_id


def _track_batch_job(job_id: str, client: Any) -> None:
    """Continuously poll the Batch client for a job's status.
    Raises an exception if the job ends in FAILED state; returns on SUCCEEDED.
    """
    while True:
        # Avoid hitting AWS throttling limits
        sleep(1.0)

        jobs = client.describe_jobs(jobs=[job_id])["jobs"]
        if not jobs:
            raise ValueError(f"Job ID {job_id} not found.")

        status = jobs[0]["status"]

        if status == "FAILED":
            reason = jobs[0]["statusReason"]
            raise Exception(
                f"Job {job_id} has failed with the following reason: {reason}"
            )

        if status == "SUCCEEDED":
            return
```

#### Set up Batch-related configuration

Add a `parameters.yml` file inside `conf/aws_batch/` with the following keys:

```yaml
aws_batch:
  job_queue: "spaceflights_queue"
  job_definition: "kedro_run"
  max_workers: 2
```

#### Update CLI implementation

Add a `cli.py` file at the same level as `settings.py`, using [the template we provide](../../getting-started/commands_reference.md#customise-or-override-project-specific-kedro-commands). Update the `run()` function so that the runner is instantiated with the correct Batch configuration:

```python
def run(tag, env, runner, is_async, node_names, to_nodes, from_nodes,
        from_inputs, to_outputs, load_versions, pipeline, pipelines,
        config, conf_source, params, namespaces, only_missing_outputs):
    """Run the pipeline."""
    runner = runner or "SequentialRunner"

    tag = _get_values_as_tuple(tag) if tag else tag
    node_names = _get_values_as_tuple(node_names) if node_names else node_names

    with KedroSession.create(
        env=env, conf_source=conf_source, runtime_params=params
    ) as session:
        runner_instance = _instantiate_runner(runner, is_async, env, pipeline, session)
        session.run(
            tags=tag,
            runner=runner_instance,
            node_names=node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_versions,
            pipeline_names=[pipeline] if pipeline else (list(pipelines) if pipelines else None),
            namespaces=namespaces,
            only_missing_outputs=only_missing_outputs,
        )
```

where the helper function `_instantiate_runner()` looks like this:

```python
def _instantiate_runner(runner, is_async, env, pipeline_name, session):
    runner_class = load_obj(runner, "kedro.runner")
    runner_kwargs = {"is_async": is_async}

    if runner.endswith("AWSBatchRunner"):
        context = session.load_context()
        batch_kwargs = context.params.get("aws_batch") or {}
        batch_kwargs["pipeline_name"] = pipeline_name or "__default__"
        batch_kwargs["env"] = env
        runner_kwargs.update(batch_kwargs)

    return runner_class(**runner_kwargs)
```

### Deploy

You're now ready to trigger the run. Execute the following command:

```bash
kedro run --env=aws_batch --pipelines=__default__ --runner=kedro_tutorial.runner.AWSBatchRunner
```

You should see jobs appearing in the AWS Batch Jobs dashboard under the `Runnable` tab as soon as resources are provisioned in the compute environment. Jobs without dependencies start immediately; jobs that depend on others wait until their `dependsOn` jobs reach `SUCCEEDED` state.

AWS Batch has native integration with CloudWatch, where you can check the logs for a particular job. You can either click on [the Batch job in the Jobs tab](https://console.aws.amazon.com/batch/home/jobs) and click `View logs` in the pop-up panel, or go to the [CloudWatch dashboard](https://console.aws.amazon.com/cloudwatch), click `Log groups` in the side bar, and find `/aws/batch/job`.
