# AWS Batch

[AWS Batch](https://aws.amazon.com/batch/) runs containerised batch jobs at scale. Each job runs in an isolated Docker container. This guide walks you through deploying a **Kedro 1.x** project so each **pipeline-level namespace** runs as one Batch job — with datasets stored on Amazon S3.

## What you will do

1. [Prepare your Kedro project](#step-1-prepare-your-kedro-project)
2. [Configure Kedro for AWS Batch](#step-2-configure-kedro-for-aws-batch)
3. [Package the Kedro project](#step-3-package-the-kedro-project)
4. [Build and push the container image](#step-4-build-and-push-the-container-image)
5. [Set up AWS Batch](#step-5-set-up-aws-batch)
6. [Create the custom Batch runner](#step-6-create-the-custom-aws-batch-runner)
7. [Customise the project CLI](#step-7-customise-the-project-cli)
8. [Submit the pipeline from your machine](#step-8-submit-the-pipeline-from-your-machine)
9. [Verify the jobs succeeded](#step-9-verify-the-jobs-succeeded)

## Before you start

### Prerequisites

- A Kedro 1.x project from the [Spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas/) (`requires-python = ">=3.10"` in `pyproject.toml`)
- Python **>=3.10** locally (the driver machine that submits Batch jobs)
- [Docker](https://docs.docker.com/get-docker/) (Podman also works if you have a `docker`-compatible CLI)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) configured for your target region
- An AWS account with permissions for Batch, S3, ECR, IAM, and EC2 (for the Batch compute environment)

Create the project with:

```bash
kedro new -s spaceflights-pandas -n spaceflights_batch
```

Name the project directory `spaceflights-batch`. Complete the [Spaceflights tutorial](../../tutorials/spaceflights_tutorial.md) if you are new to the project layout.

### Strategy

A custom **`AWSBatchRunner`** runs on your local machine (or a CI agent). It does **not** execute node logic itself. Instead, it:

1. Groups the pipeline by top-level namespace with `Pipeline.group_nodes_by("namespace")`
2. Submits one AWS Batch job per namespace group, with `dependsOn` links between jobs
3. Polls Batch until each job reaches `SUCCEEDED` or `FAILED`

Each Batch job runs every node in that namespace inside the container using your packaged project CLI (for example `spaceflights-batch run --env aws_batch --namespaces data_processing --conf-source /app/conf`).

For Spaceflights `__default__`, this creates **three** Batch jobs (`data_processing`, `data_science`, and `reporting`) instead of one per node.

This matches [grouping nodes for deployment](../nodes_grouping.md) and the [AWS Step Functions guide](aws_step_functions.md).

Because containers are isolated, every dataset shared between namespace groups must use persistent storage (for example S3). `MemoryDataset` entries cannot be shared between Batch jobs.

Use **pipeline-level namespaces** (defined on the `Pipeline` object), not node-level namespaces. Node-level namespaces are for Kedro-Viz layout and do not group execution.

!!! note "Submitting without pipeline-level namespaces"
    If your project has no pipeline-level namespaces, `AWSBatchRunner` still works. Each node without a namespace becomes its own group — **one Batch job per node** with `--nodes <node_name>`.

    Skip [Assign pipeline-level namespaces](#assign-pipeline-level-namespaces) and continue from Step 2. Expect more jobs and longer runtime; add namespaces later for coarser grouping.

### Placeholders used in this guide

| Placeholder | Example |
| --- | --- |
| `<your-bucket>` | `kedro-batch-test-123456789012` |
| `<your-aws-account-id>` | `123456789012` |
| `<your-aws-region>` | `us-east-1` |
| `<PACKAGE_NAME>` | `spaceflights_batch` |
| `<PACKAGE_CLI>` | `spaceflights-batch` |
| `<ecr-image-uri>` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/spaceflights-batch:latest` |
| `<batch-job-role-arn>` | IAM role ARN for Batch jobs (S3 access) |
| `<batch-job-queue>` | `spaceflights_queue` |
| `<batch-job-definition>` | `kedro_run` |

---

## Step 1: Prepare your Kedro project

From the project root, install dependencies and run the pipeline locally:

```bash
pip install -e .
kedro run
```

Keep `conf/base/catalog.yml` on **local file paths** for local development. You add S3 paths in a separate environment in the next step.

Each node should have a meaningful `name` in its `Node(...)` definition. Batch job names and log streams use namespace or node names.

### Assign pipeline-level namespaces

This step is **recommended** for fewer Batch jobs and lower orchestration overhead. If your pipeline has no pipeline-level namespaces, skip to [Step 2](#step-2-configure-kedro-for-aws-batch) — see the note under [Strategy](#strategy).

Before deploying, assign a **pipeline-level namespace** to each sub-pipeline you want to run as one Batch job. In Spaceflights, update `create_pipeline()` in each module under `src/<PACKAGE_NAME>/pipelines/`:

```python
def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            # ... nodes unchanged ...
        ],
        namespace="data_processing",
        prefix_datasets_with_namespace=False,
        inputs={"companies", "shuttles", "reviews"},
        outputs={"model_input_table"},
    )
```

Set `prefix_datasets_with_namespace=False` so dataset names in `conf/base/catalog.yml` and `conf/aws_batch/catalog.yml` keep their original names. Declare explicit `inputs` and `outputs` for each namespace.

| Sub-pipeline | `namespace` | `inputs` | `outputs` |
| --- | --- | --- | --- |
| `data_science` | `data_science` | `{"model_input_table"}` | `{"regressor", "X_train", "X_test", "y_train", "y_test"}` |
| `reporting` | `reporting` | `{"preprocessed_shuttles"}` | `{"shuttle_passenger_capacity_plot_exp", "shuttle_passenger_capacity_plot_go", "dummy_confusion_matrix"}` |

See [Group nodes with namespaces](../../build/namespaces.md#group-nodes-with-namespaces) for the full Spaceflights example.

!!! note "Update `conf/base/catalog.yml` for reporting"
    If the starter lists `matplotlib.MatplotlibWriter` for `dummy_confusion_matrix`, change it to `matplotlib.MatplotlibDataset` in **`conf/base/catalog.yml`** before running locally.

Verify locally after adding namespaces:

```bash
kedro run --namespaces=data_processing
kedro run
```

---

## Step 2: Configure Kedro for AWS Batch

### Create an `aws_batch` config environment

Add `conf/aws_batch/` with `globals.yml`, `catalog.yml`, and `parameters.yml`. Use [catalog globals](https://docs.kedro.org/en/stable/configure/advanced_configuration.html#how-to-use-globals-and-runtime-params) for the S3 bucket name.

`conf/aws_batch/globals.yml`:

```yaml
s3_bucket: <your-bucket>
```

`conf/aws_batch/parameters.yml` (used by the custom runner in Step 7):

```yaml
aws_batch:
  job_queue: <batch-job-queue>
  job_definition: <batch-job-definition>
  max_workers: 4
  package_cli: <PACKAGE_CLI>
  conf_source: /app/conf
```

!!! warning "Catalog environment merge is destructive"
    By default, Kedro merges configuration environments at the **top level**. If `conf/aws_batch/catalog.yml` overrides a dataset using `filepath` alone, it **replaces** the entire dataset entry from `conf/base/` and drops keys such as `type`. Either include the full dataset definition (including `type`) in `conf/aws_batch/catalog.yml`, or set `merge_strategy: {catalog: soft}` in `settings.py` so environment files can override individual fields.

!!! warning "Every shared dataset needs S3 storage"
    The `aws_batch` catalog must list **every** dataset used by the deployed pipeline, including intermediate outputs such as `X_train` and reporting artefacts. Omitting a dataset causes `MemoryDataset` errors when Batch moves between jobs.

### Add dependencies

Add `s3fs` and `boto3` to `pyproject.toml`:

```toml
"s3fs>=2024.6.0",
"boto3>=1.34.0",
```

The Spaceflights starter uses Parquet for intermediate tables. Use `matplotlib.MatplotlibDataset` (not the legacy `MatplotlibWriter` type).

??? example "View `conf/aws_batch/catalog.yml`"
    ```yaml
    companies:
      type: pandas.CSVDataset
      filepath: s3://${globals:s3_bucket}/01_raw/companies.csv

    reviews:
      type: pandas.CSVDataset
      filepath: s3://${globals:s3_bucket}/01_raw/reviews.csv

    shuttles:
      type: pandas.ExcelDataset
      filepath: s3://${globals:s3_bucket}/01_raw/shuttles.xlsx
      load_args:
        engine: openpyxl

    preprocessed_companies:
      type: pandas.ParquetDataset
      filepath: s3://${globals:s3_bucket}/02_intermediate/preprocessed_companies.parquet

    preprocessed_shuttles:
      type: pandas.ParquetDataset
      filepath: s3://${globals:s3_bucket}/02_intermediate/preprocessed_shuttles.parquet

    model_input_table:
      type: pandas.ParquetDataset
      filepath: s3://${globals:s3_bucket}/03_primary/model_input_table.parquet

    X_train:
      type: pickle.PickleDataset
      filepath: s3://${globals:s3_bucket}/04_feature/X_train.pickle

    X_test:
      type: pickle.PickleDataset
      filepath: s3://${globals:s3_bucket}/04_feature/X_test.pickle

    y_train:
      type: pickle.PickleDataset
      filepath: s3://${globals:s3_bucket}/04_feature/y_train.pickle

    y_test:
      type: pickle.PickleDataset
      filepath: s3://${globals:s3_bucket}/04_feature/y_test.pickle

    regressor:
      type: pickle.PickleDataset
      filepath: s3://${globals:s3_bucket}/06_models/regressor.pickle
      versioned: true

    shuttle_passenger_capacity_plot_exp:
      type: plotly.PlotlyDataset
      filepath: s3://${globals:s3_bucket}/08_reporting/shuttle_passenger_capacity_plot_exp.json
      versioned: true
      plotly_args:
        type: bar
        fig:
          x: shuttle_type
          y: passenger_capacity
          orientation: h
        layout:
          xaxis_title: Shuttles
          yaxis_title: Average passenger capacity
          title: Shuttle Passenger capacity

    shuttle_passenger_capacity_plot_go:
      type: plotly.JSONDataset
      filepath: s3://${globals:s3_bucket}/08_reporting/shuttle_passenger_capacity_plot_go.json
      versioned: true

    dummy_confusion_matrix:
      type: matplotlib.MatplotlibDataset
      filepath: s3://${globals:s3_bucket}/08_reporting/dummy_confusion_matrix.png
      versioned: true
    ```

### Create an S3 bucket and upload raw data

```bash
export AWS_REGION=<your-aws-region>
export S3_BUCKET=<your-bucket>

aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"
aws s3 sync data/01_raw/ "s3://${S3_BUCKET}/01_raw/"
```

!!! note "`shuttles.xlsx` may be missing locally"
    The starter gitignores `data/01_raw/shuttles.xlsx`. Copy it from the [starter repository](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas) if `kedro new` did not place it in your project.

### Verify the AWS Batch environment locally

```bash
kedro run --env aws_batch
```

Confirm outputs appear under your S3 bucket paths.

---

## Step 3: Package the Kedro project

```bash
kedro package
```

This creates a `.whl` in `dist/`. See [Package a Kedro project](../package_a_project.md#package-a-kedro-project) for details.

---

## Step 4: Build and push the container image

Create a `Dockerfile` in your project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

COPY conf/ /app/conf/
```

!!! tip "Apple Silicon (ARM) builders"
    Batch on EC2 compute environments uses **`x86_64`** instances. Build with `--platform linux/amd64` (Docker or Podman).

```bash
export ECR_IMAGE=<ecr-image-uri>

kedro package
docker build --platform linux/amd64 -t ${ECR_IMAGE} .
```

Push to ECR — see [Pushing a Docker image to an Amazon ECR repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html):

```bash
aws ecr create-repository --repository-name spaceflights-batch --region <your-aws-region>
aws ecr get-login-password --region <your-aws-region> | \
  docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<your-aws-region>.amazonaws.com
docker push ${ECR_IMAGE}
```

!!! note "Trim dependencies for production images"
    The Spaceflights starter includes Jupyter and Kedro-Viz, which increase image size. For production Batch images, consider a slimmer `requirements` subset or a multi-stage Dockerfile that omits development dependencies.

---

## Step 5: Set up AWS Batch

Complete this setup for each AWS account/region. Follow the linked AWS guides — this section lists Kedro-specific settings.

| Resource | AWS documentation | What you need for Kedro |
| --- | --- | --- |
| **S3 bucket** | [Creating a bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html) | Raw data and pipeline outputs |
| **ECR repository** | [Create a private repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html) | Container image from Step 4 |
| **IAM job role** | [IAM roles for Batch](https://docs.aws.amazon.com/batch/latest/userguide/IAM_policies.html) | S3 read/write for datasets; attach to the job definition as `jobRoleArn` |
| **Compute environment** | [Compute environments](https://docs.aws.amazon.com/batch/latest/userguide/compute_environments.html) | Managed EC2 environment (for example `spaceflights_env`) |
| **Job queue** | [Job queues](https://docs.aws.amazon.com/batch/latest/userguide/job_queues.html) | Links jobs to the compute environment (for example `spaceflights_queue`) |
| **Job definition** | [Job definitions](https://docs.aws.amazon.com/batch/latest/userguide/job_definitions.html) | Points at `<ecr-image-uri>`; leave `command` empty (overridden per node) |

!!! warning "Avoid overly broad IAM policies"
    Older tutorials attach `AmazonS3FullAccess` to the job role. For production, scope the policy to your bucket ARN.

### Job definition settings (Kedro-specific)

When creating the job definition (for example `kedro_run`), set:

| Setting | Recommended value |
| --- | --- |
| **Image** | `<ecr-image-uri>` |
| **vCPUs** | `2` |
| **Memory** | `4096` MiB (increase for heavy modelling nodes) |
| **Job role** | `<batch-job-role-arn>` with S3 access |
| **Timeout** | `3600` seconds or higher |
| **Command** | leave empty (the runner overrides per job) |

The compute environment does not launch instances until jobs are submitted, so creating it does not incur immediate cost.

---

## Step 6: Create the custom AWS Batch runner

Create `src/<PACKAGE_NAME>/runner/batch_runner.py` with an `AWSBatchRunner` class that extends `AbstractRunner` and submits Batch jobs for each namespace group (or each node when no namespace is defined).

??? example "View `batch_runner.py`"
    ```python
    """``AWSBatchRunner`` submits Kedro namespace groups as AWS Batch jobs."""

    from __future__ import annotations

    from concurrent.futures import ThreadPoolExecutor
    from time import sleep
    from typing import Any

    import boto3
    from pluggy import PluginManager

    from kedro.io import CatalogProtocol
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import GroupedNodes
    from kedro.runner import AbstractRunner


    def _track_batch_job(job_id: str, client: Any) -> None:
        """Poll Batch until the job succeeds or raises on failure."""
        while True:
            sleep(1.0)
            jobs = client.describe_jobs(jobs=[job_id])["jobs"]
            if not jobs:
                raise ValueError(f"Job ID {job_id} not found.")

            job = jobs[0]
            status = job["status"]

            if status == "FAILED":
                reason = job.get("statusReason", "unknown")
                raise RuntimeError(f"Job {job_id} failed: {reason}")

            if status == "SUCCEEDED":
                return


    class AWSBatchRunner(AbstractRunner):
        """Submit Kedro namespace groups to AWS Batch with dependency ordering."""

        def __init__(
            self,
            job_queue: str,
            job_definition: str,
            max_workers: int | None = None,
            package_cli: str | None = None,
            conf_source: str | None = None,
            is_async: bool = False,
        ):
            super().__init__(is_async=is_async)
            self._job_queue = job_queue
            self._job_definition = job_definition
            self._max_workers = max_workers
            self._package_cli = package_cli or "kedro"
            self._conf_source = conf_source
            self._client = boto3.client("batch")

        def _get_required_workers_count(self, groups: list[GroupedNodes]) -> int:
            required = len(groups)
            if self._max_workers is not None:
                return min(required, self._max_workers)
            return required

        def _get_executor(self, max_workers: int):
            return ThreadPoolExecutor(max_workers=max_workers)

        def _run(
            self,
            pipeline: Pipeline,
            catalog: CatalogProtocol,
            hook_manager: PluginManager | None = None,
            run_id: str | None = None,
        ) -> None:
            groups = pipeline.group_nodes_by("namespace")
            group_map = {group.name: group for group in groups}
            group_deps = {group.name: set(group.dependencies) for group in groups}

            todo_groups = set(group_map.keys())
            group_to_job: dict[str, str] = {}
            done_groups: set[str] = set()
            futures: set = set()
            max_workers = self._get_required_workers_count(groups)

            self._logger.info("Max workers: %d", max_workers)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                while True:
                    done = {fut for fut in futures if fut.done()}
                    futures -= done
                    for future in done:
                        try:
                            group_name = future.result()
                        except Exception:
                            self._suggest_resume_scenario(
                                pipeline, set(), catalog
                            )
                            raise
                        done_groups.add(group_name)
                        self._logger.info(
                            "Completed %d out of %d jobs",
                            len(done_groups),
                            len(groups),
                        )

                    ready = {
                        name
                        for name in todo_groups
                        if group_deps[name] <= done_groups
                    }
                    todo_groups -= ready
                    for name in ready:
                        future = pool.submit(
                            self._submit_job,
                            group_map[name],
                            group_to_job,
                            group_deps[name],
                            run_id,
                        )
                        futures.add(future)

                    if not futures:
                        if todo_groups:
                            raise RuntimeError(
                                f"Unresolved groups: {sorted(todo_groups)}"
                            )
                        break

        def _submit_job(
            self,
            group: GroupedNodes,
            group_to_job: dict[str, str],
            group_dependencies: set[str],
            run_id: str | None,
        ) -> str:
            self._logger.info("Submitting the job for group: %s", group.name)

            run_suffix = run_id or "local"
            job_name = f"kedro-{run_suffix}-{group.name}".replace(".", "-")[:128]
            depends_on = [
                {"jobId": group_to_job[dep]}
                for dep in group_dependencies
                if dep in group_to_job
            ]

            command = [
                self._package_cli,
                "run",
                "--env",
                "aws_batch",
            ]
            if group.type == "namespace":
                command.extend(["--namespaces", group.name])
            else:
                command.extend(["--nodes", group.nodes[0]])
            if self._conf_source:
                command.extend(["--conf-source", self._conf_source])

            response = self._client.submit_job(
                jobName=job_name,
                jobQueue=self._job_queue,
                jobDefinition=self._job_definition,
                dependsOn=depends_on,
                containerOverrides={"command": command},
            )

            job_id = response["jobId"]
            group_to_job[group.name] = job_id
            _track_batch_job(job_id, self._client)
            return group.name
    ```

Export the runner from `src/<PACKAGE_NAME>/runner/__init__.py`:

```python
from .batch_runner import AWSBatchRunner

__all__ = ["AWSBatchRunner"]
```

---

## Step 7: Customise the project CLI

Kedro's built-in `kedro run` passes `is_async` to the runner constructor and nothing else. `AWSBatchRunner` needs `job_queue`, `job_definition`, and other settings from `conf/aws_batch/parameters.yml`.

Add `src/<PACKAGE_NAME>/cli.py` using [the project CLI template](../../getting-started/commands_reference.md#customise-or-override-project-specific-kedro-commands). Override the `run` command so the runner is constructed with Batch parameters from the active Kedro session:

```python
def _instantiate_runner(runner: str, is_async: bool, params: dict[str, Any]):
    runner_class = load_obj(runner or "SequentialRunner", "kedro.runner")
    runner_kwargs: dict[str, Any] = {"is_async": is_async}
    if runner.endswith("AWSBatchRunner"):
        batch_kwargs = params.get("aws_batch") or {}
        runner_kwargs.update(batch_kwargs)
    return runner_class(**runner_kwargs)
```

Inside `run()`, create the session, build the runner from `session.params`, and pass it to `session.run()`:

```python
with KedroSession.create(
    env=env, conf_source=conf_source, runtime_params=params
) as session:
    runner_instance = _instantiate_runner(runner, is_async, dict(session.params))
    return session.run(
        runner=runner_instance,
        # ... other run arguments ...
    )
```

See the [common use cases guide](../../extend/common_use_cases.md) for more on customising Kedro commands.

---

## Step 8: Submit the pipeline from your machine

From your project root (with AWS credentials configured), use your packaged project CLI and the custom runner:

```bash
spaceflights-batch run \
  --env aws_batch \
  --runner spaceflights_batch.runner.AWSBatchRunner
```

The `AWSBatchRunner` on your machine submits Batch jobs. Each job runs inside the container image and executes one namespace group (or a single node when no namespace is defined). For Spaceflights `__default__`, expect **three** jobs.

Track jobs in the [Batch console](https://console.aws.amazon.com/batch/) or with:

```bash
aws batch list-jobs --job-queue <batch-job-queue> --job-status RUNNING
```

Logs are available in [CloudWatch Logs](https://docs.aws.amazon.com/batch/latest/userguide/monitoring.html) under `/aws/batch/job`.

---

## Step 9: Verify the jobs succeeded

1. **Check Batch job states** — all jobs should reach **SUCCEEDED**.

```bash
aws batch list-jobs --job-queue <batch-job-queue> --job-status SUCCEEDED
```

2. **Check S3 outputs** — list paths from your `conf/aws_batch/catalog.yml`:

```bash
aws s3 ls "s3://<your-bucket>/" --recursive
```

You should see objects under `02_intermediate/`, `03_primary/`, `04_feature/`, `06_models/`, and `08_reporting/`.

If jobs failed, see [Troubleshooting](#troubleshooting).

---

## Troubleshooting

<!-- vale off -->

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Cannot install ... s3fs` dependency conflict | `kedro-viz` pins an older `s3fs` range | Use `s3fs>=2021.4` locally; omit Kedro-Viz from the Batch image for production |
| `AccessDenied` on S3 inside Batch jobs | Job role lacks bucket permissions | Attach an IAM policy scoped to `<your-bucket>` on the job role |
| `MemoryDataset` errors between jobs | Dataset missing from `conf/aws_batch/catalog.yml` | Add S3-backed entries for all shared datasets |
| Batch job times out mid-namespace | Namespace contains too much work for one job timeout | Split namespaces further or increase job definition timeout/memory |
| `Dataset 'MatplotlibWriter' not found` | Outdated dataset type in `conf/base/catalog.yml` | Use `matplotlib.MatplotlibDataset` in base and aws_batch catalogs |
| S3 errors during `kedro run --env aws_batch` locally | Missing AWS CRT support in `botocore` | Run `pip install 'botocore[crt]'` and retry |
| Jobs stuck in `RUNNABLE` | Compute environment not scaled or no capacity | Check compute environment status; increase `maxvCpus` or instance types |
| `Essential container exited` immediately | Wrong `--conf-source` or missing `conf/` in image | Verify `COPY conf/ /app/conf/` in the Dockerfile and `conf_source: /app/conf` in parameters |
| `ModuleNotFoundError` for runner kwargs | Built-in `kedro run` used instead of custom `cli.py` | Use `<PACKAGE_CLI> run` after adding the customised `cli.py` from Step 7 |
| Job fails with out-of-memory | Default 2 GB too low for sklearn/matplotlib nodes | Increase memory in the job definition (for example `4096` or `8192` MiB) |

<!-- vale on -->

---

## Limitations

- Each Batch job runs **one namespace group** (or one node when no namespace is defined). A namespace must finish within the job definition timeout and memory limits.
- Pipelines with dozens of nodes without namespaces increase Batch job count and ECR pulls; add pipeline-level namespaces or use [Amazon EMR Serverless](amazon_emr_serverless.md) for Spark-heavy workloads.
- The driver machine (where you run `AWSBatchRunner`) must stay online until all jobs complete.
- Batch job dependencies use AWS Batch `dependsOn`; this matches Kedro's DAG but does not replace Kedro's own `ThreadRunner` parallelism on a single machine.

---

## Further reading

### Kedro

- [Running Kedro in a distributed environment](../distributed.md)
- [Grouping nodes for deployment](../nodes_grouping.md)
- [Group nodes with namespaces](../../build/namespaces.md#group-nodes-with-namespaces)
- [Package a Kedro project](../package_a_project.md)
- [Customise project-specific Kedro commands](../../getting-started/commands_reference.md#customise-or-override-project-specific-kedro-commands)
- [Catalog globals](https://docs.kedro.org/en/stable/configure/advanced_configuration.html#how-to-use-globals-and-runtime-params)

### AWS

- [AWS Batch User Guide](https://docs.aws.amazon.com/batch/latest/userguide/what-is-aws-batch.html)
- [Creating a job definition](https://docs.aws.amazon.com/batch/latest/userguide/job_definitions.html)
- [IAM policies for Batch](https://docs.aws.amazon.com/batch/latest/userguide/IAM_policies.html)
- [Pushing a Docker image to ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html)
- [Batch monitoring and logging](https://docs.aws.amazon.com/batch/latest/userguide/monitoring.html)
