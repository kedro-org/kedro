# AWS Step Functions

[AWS Step Functions](https://aws.amazon.com/step-functions/) orchestrates [AWS Lambda](https://aws.amazon.com/lambda/) functions into a state machine. This guide walks you through deploying a **Kedro 1.x** project so each pipeline node runs as a Lambda function, with datasets stored on Amazon S3.

## What you will do

1. [Prepare your Kedro project](#step-1-prepare-your-kedro-project)
2. [Configure Kedro for AWS](#step-2-configure-kedro-for-aws)
3. [Package the Kedro project](#step-3-package-the-kedro-project)
4. [Set up AWS](#step-4-set-up-aws)
5. [Create the Lambda handler](#step-5-create-the-lambda-handler)
6. [Build the Lambda container image](#step-6-build-the-lambda-container-image)
7. [Write the CDK deployment script](#step-7-write-the-cdk-deployment-script)
8. [Deploy with CDK](#step-8-deploy-with-cdk)
9. [Run the state machine](#step-9-run-the-state-machine)
10. [Verify outputs on S3](#step-10-verify-outputs-on-s3)

The deployed state machine looks like this in the AWS Management Console:

![](../../meta/images/aws_step_functions_state_machine.png)

## Before you start

### Prerequisites

- A Kedro 1.x project from the [Spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas/) (`requires-python = ">=3.10"` in `pyproject.toml`)
- Python **>=3.10** locally
- [Docker](https://docs.docker.com/get-docker/) (Podman also works if you have a `docker`-compatible CLI)
- [Node.js](https://nodejs.org/) and the [CDK CLI](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) (`npm install -g aws-cdk`)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) configured for your target region
- An AWS account with permissions for S3, ECR, Lambda, Step Functions, IAM, and CloudFormation

Create the project with:

```bash
kedro new -s spaceflights-pandas -n spaceflights_step_functions
```

Name the project directory `spaceflights-step-functions`. Complete the [Spaceflights tutorial](../../tutorials/spaceflights_tutorial.md) if you are new to the project layout.

### Strategy

Each Kedro node becomes a Lambda function that shares the same container image. Step Functions runs nodes in parallel within each dependency group and sequentially across groups, following the same principles as [running Kedro in a distributed environment](../distributed.md).

Because Lambda functions are isolated, every dataset that crosses node boundaries must use persistent storage (for example S3). `MemoryDataset` entries cannot be shared between functions.

### Why a container image?

Lambda [container images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html) let you package Kedro, project dependencies, and configuration into one artefact you can build and test locally before pushing to [Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html). The [AWS Lambda Python 3.12 base image](https://gallery.ecr.aws/lambda/python) provides the runtime interface; your `Dockerfile` installs the packaged Kedro wheel and copies `conf/`.

### Placeholders used in this guide

Replace these before building and deploying:

| Placeholder | Example |
| --- | --- |
| `<your-bucket>` | `kedro-sfn-test-123456789012` |
| `<your-aws-account-id>` | `123456789012` |
| `<your-aws-region>` | `us-east-1` |
| `<PACKAGE_NAME>` | `spaceflights_step_functions` |
| `<ecr-image-uri>` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/spaceflights-step-functions:latest` |

---

## Step 1: Prepare your Kedro project

From the project root, install dependencies and run the pipeline locally:

```bash
pip install -e .
kedro run
```

Keep `conf/base/catalog.yml` on **local file paths** for local development. You add S3 paths in a separate environment in the next step.

---

## Step 2: Configure Kedro for AWS

### Create an `aws` config environment

Add `conf/aws/` with a `globals.yml` file and a `catalog.yml` that points every dataset to S3. Use [catalog globals](https://docs.kedro.org/en/stable/configure/advanced_configuration.html#how-to-use-globals-and-runtime-params) so the bucket name is defined in one place.

`conf/aws/globals.yml`:

```yaml
s3_bucket: <your-bucket>
```

!!! warning "Catalog environment merge is destructive"
    By default, Kedro merges configuration environments at the **top level**. If `conf/aws/catalog.yml` overrides a dataset using `filepath` alone, it **replaces** the entire dataset entry from `conf/base/` and drops keys such as `type`. Either include the full dataset definition (including `type`) in `conf/aws/catalog.yml`, or set `merge_strategy: {catalog: soft}` in `settings.py` so environment files can override individual fields.

!!! warning "Every shared dataset needs S3 storage"
    The `aws` catalog must list **every** dataset used by the deployed pipeline, including intermediate outputs such as `X_train`, `X_test`, `y_train`, and `y_test`, and reporting artefacts. Omitting a dataset causes `MemoryDataset` errors when Step Functions moves between Lambda invocations.

### Add `s3fs` to project dependencies

When datasets read from `s3://` paths, add `s3fs` to `pyproject.toml`:

```toml
"s3fs>=2024.6.0"
```

The Spaceflights starter uses Parquet for intermediate tables and includes a reporting pipeline.

??? example "View `conf/aws/catalog.yml`"
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

Create a globally unique bucket and upload the raw datasets — see [Creating a bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html) and [Uploading objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html):

```bash
export AWS_REGION=<your-aws-region>
export S3_BUCKET=<your-bucket>

aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"
aws s3 sync data/01_raw/ "s3://${S3_BUCKET}/01_raw/"
```

!!! note "`shuttles.xlsx` may be missing locally"
    The starter gitignores `data/01_raw/shuttles.xlsx`. Copy it from the [starter repository](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas) if `kedro new` did not place it in your project.

### Verify the AWS environment locally

```bash
kedro run --env aws
```

Confirm outputs appear under your S3 bucket paths.

### How config reaches Lambda

`kedro package` produces a `.whl` file; the wheel does **not** include `conf/`. The `Dockerfile` copies the `conf/` directory into `${LAMBDA_TASK_ROOT}/conf`. The handler passes `conf_source` to `KedroSession.create()` so Kedro loads the `aws` environment from that path.

---

## Step 3: Package the Kedro project

Run this in your project root. Repeat whenever you change pipeline code or dependencies:

```bash
kedro package
```

This creates `dist/spaceflights_step_functions-0.1-py3-none-any.whl` (the exact filename depends on your package version). See [Package a Kedro project](../package_a_project.md#package-a-kedro-project) for details.

---

## Step 4: Set up AWS

Complete this setup for each AWS account/region. Follow the linked AWS guides for console and CLI steps — this section lists what you need and Kedro-specific settings.

| Resource | AWS documentation | What you need for Kedro |
| --- | --- | --- |
| **S3 bucket** | [Creating a bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html) | Store raw data and pipeline outputs (`s3://<your-bucket>/01_raw/`, `02_intermediate/`, and so on) |
| **ECR repository** | [Create a private repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html) | One **private** repo for the Lambda image (for example `spaceflights-step-functions`) |
| **CDK bootstrap** | [Bootstrapping](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html) | One-time per account/region before `cdk deploy` |
| **IAM** | Created by CDK | Lambda execution roles and Step Functions permissions are provisioned by the CDK stack |

```bash
export AWS_ACCOUNT_ID=<your-aws-account-id>
export AWS_REGION=<your-aws-region>
export ECR_REPO=spaceflights-step-functions

aws ecr create-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}"
```

---

## Step 5: Create the Lambda handler

Create `lambda_handler.py` in the project root. Each Lambda invocation runs a single node named in the event payload.

!!! note "Use `configure_project` inside Lambda"
    Call `configure_project("<PACKAGE_NAME>")` in the handler, not `bootstrap_project()`. The packaged wheel is installed into the container; `bootstrap_project()` expects `pyproject.toml` and a `src/` tree that are not copied into the image.

```python
from pathlib import Path
from unittest.mock import patch


def handler(event, context):
    """AWS Lambda entrypoint that runs a single Kedro node."""
    from kedro.framework.project import configure_project
    from kedro.framework.session import KedroSession

    node_to_run = event["node_name"]
    project_path = Path(__file__).resolve().parent

    # SemLock is not available on Lambda; mock it so Kedro can import safely.
    with patch("multiprocessing.Lock"):
        configure_project("spaceflights_step_functions")
        with KedroSession.create(
            project_path=project_path,
            env="aws",
            conf_source=str(project_path / "conf"),
        ) as session:
            session.run(node_names=[node_to_run])
```

Replace `spaceflights_step_functions` with your package name if you used a different starter.

---

## Step 6: Build the Lambda container image

Create a `Dockerfile` in your project root:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY conf/ ${LAMBDA_TASK_ROOT}/conf/

COPY dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl --target "${LAMBDA_TASK_ROOT}" \
    && rm -f /tmp/*.whl

CMD ["lambda_handler.handler"]
```

!!! tip "Apple Silicon (ARM) builders"
    Lambda functions use **`x86_64`** by default. Build with `--platform linux/amd64` (Docker or Podman) or invocations may fail with `Runtime.InvalidEntrypoint` / `ProcessSpawnFailed`.

Build the image. Tag it with your ECR URI at build time so the image you push is the one you built:

```bash
export ECR_IMAGE=<ecr-image-uri>

kedro package
docker build --platform linux/amd64 -t ${ECR_IMAGE} .
```

If you build with a local tag (for example `spaceflights-step-functions`), run `docker tag spaceflights-step-functions:latest <ecr-image-uri>` right before pushing.

### Push to ECR

See [Pushing a Docker image to an Amazon ECR repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html):

```bash
aws ecr get-login-password --region <your-aws-region> | \
  docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<your-aws-region>.amazonaws.com
docker push ${ECR_IMAGE}
```

!!! note "Re-push after handler or catalog changes"
    When you change `lambda_handler.py`, `conf/aws/`, or rebuild the wheel, push a new image tag and update each Lambda function. If you reuse an existing CDK stack, run `aws lambda update-function-code --image-uri <ecr-image-uri>` on each image-based function, or redeploy with `cdk deploy`.

---

## Step 7: Write the CDK deployment script

Install CDK Python dependencies into the **same environment** as your Kedro project:

`deploy_requirements.txt`:

```
aws-cdk-lib>=2.170.0
constructs>=10.0.0
```

```bash
pip install -r deploy_requirements.txt
```

Create `deploy.py`. This script reads the Kedro pipeline, creates one Lambda function per node, and wires them into a Step Functions state machine. Update `s3_data_bucket_name` to match your bucket.

??? example "View `deploy.py`"
    ```python
    import re
    from pathlib import Path

    import aws_cdk as cdk
    from aws_cdk import (
        Duration,
        Stack,
        aws_ecr as ecr,
        aws_lambda as lambda_,
        aws_s3 as s3,
        aws_stepfunctions as sfn,
        aws_stepfunctions_tasks as tasks,
    )
    from constructs import Construct
    from kedro.framework.project import pipelines
    from kedro.framework.startup import bootstrap_project
    from kedro.pipeline.node import Node


    def _clean_name(name: str) -> str:
        """Reformat a name to be compliant with AWS naming rules."""
        return re.sub(r"[\W_]+", "-", name).strip("-")[:63]


    class KedroStepFunctionsStack(Stack):
        """A CDK stack that deploys a Kedro pipeline to AWS Step Functions."""

        env_name = "aws"
        project_path = Path.cwd()
        ecr_repository_name = project_path.name
        s3_data_bucket_name = "<your-bucket>"

        def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
            super().__init__(scope, construct_id, **kwargs)

            self._parse_kedro_pipeline()
            self._set_ecr_repository()
            self._set_ecr_image()
            self._set_s3_data_bucket()
            self._convert_kedro_pipeline_to_step_functions_state_machine()

        def _parse_kedro_pipeline(self) -> None:
            """Extract the Kedro pipeline from the project"""
            metadata = bootstrap_project(self.project_path)

            self.project_name = metadata.project_name
            self.pipeline = pipelines["__default__"]

        def _set_ecr_repository(self) -> None:
            """Set the ECR repository for the Lambda base image"""
            self.ecr_repository = ecr.Repository.from_repository_name(
                self, id="ECR", repository_name=self.ecr_repository_name
            )

        def _set_ecr_image(self) -> None:
            """Set the Lambda base image"""
            self.ecr_image = lambda_.EcrImageCode.from_ecr_image(
                repository=self.ecr_repository, tag_or_digest="latest"
            )

        def _set_s3_data_bucket(self) -> None:
            """Set the S3 bucket containing the raw data"""
            self.s3_bucket = s3.Bucket.from_bucket_name(
                self, "RawDataBucket", self.s3_data_bucket_name
            )

        def _convert_kedro_node_to_lambda_function(self, node: Node) -> lambda_.Function:
            """Convert a Kedro node into an AWS Lambda function"""
            func = lambda_.Function(
                self,
                id=_clean_name(f"{node.name}_fn"),
                description=str(node),
                code=self.ecr_image,
                handler=lambda_.Handler.FROM_IMAGE,
                runtime=lambda_.Runtime.FROM_IMAGE,
                environment={
                    "S3_BUCKET": self.s3_data_bucket_name,
                    "MPLCONFIGDIR": "/tmp/matplotlib",
                },
                function_name=_clean_name(node.name),
                memory_size=1024,
                timeout=Duration.minutes(15),
            )
            self.s3_bucket.grant_read_write(func)
            return func

        def _convert_kedro_node_to_sfn_task(self, node: Node) -> tasks.LambdaInvoke:
            """Convert a Kedro node into an AWS Step Functions Task"""
            return tasks.LambdaInvoke(
                self,
                _clean_name(node.name),
                lambda_function=self._convert_kedro_node_to_lambda_function(node),
                payload=sfn.TaskInput.from_object({"node_name": node.name}),
            )

        def _convert_kedro_pipeline_to_step_functions_state_machine(self) -> None:
            """Convert Kedro pipeline into an AWS Step Functions State Machine"""
            definition = sfn.Pass(self, "Start")

            for index, group in enumerate(self.pipeline.grouped_nodes, start=1):
                group_name = f"Group {index}"
                parallel_state = sfn.Parallel(self, group_name)
                for node in group:
                    parallel_state.branch(self._convert_kedro_node_to_sfn_task(node))
                definition = definition.next(parallel_state)

            sfn.StateMachine(
                self,
                self.project_name,
                definition=definition,
                timeout=Duration.minutes(60),
            )


    app = cdk.App()
    KedroStepFunctionsStack(app, "KedroStepFunctionsStack")
    app.synth()
    ```

Register the app with CDK by creating `cdk.json`:

```json
{
  "app": "python deploy.py"
}
```

!!! note "Match the Python interpreter in `cdk.json`"
    `deploy.py` calls `bootstrap_project()` and needs both Kedro and `aws-cdk-lib` installed. If your system `python3` differs from the environment where you installed dependencies, point `app` at that interpreter (for example `.venv/bin/python deploy.py`).

---

## Step 8: Deploy with CDK

Bootstrap CDK in your account (first time per account/region) and deploy the stack — see [AWS CDK bootstrapping](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html):

```bash
cdk bootstrap "aws://<your-aws-account-id>/<your-aws-region>"
cdk deploy
```

After deployment, open the [Step Functions console](https://console.aws.amazon.com/states/) to see the state machine:

![](../../meta/images/aws_step_functions_state_machine_listing.png)

You will also see one Lambda function per Kedro node:

![](../../meta/images/aws_lambda_functions.png)

The CloudFormation stack `KedroStepFunctionsStack` should reach **`CREATE_COMPLETE`**.

---

## Step 9: Run the state machine

Start an execution from the [Step Functions console](https://console.aws.amazon.com/states/) or with the AWS CLI — see [Starting a state machine execution](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-creating-lambda-state-machine.html):

```bash
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name, 'spaceflights')].stateMachineArn | [0]" \
  --output text)

aws stepfunctions start-execution \
  --state-machine-arn "${STATE_MACHINE_ARN}" \
  --name "kedro-run-$(date +%s)"
```

Poll until the execution status is **`SUCCEEDED`**.

---

## Step 10: Verify outputs on S3

1. **Check execution status** — confirm the Step Functions run reached **SUCCEEDED**.

2. **Check S3 outputs** — list the output paths from your `conf/aws/catalog.yml`. See [Listing objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingObjects.html):

```bash
aws s3 ls "s3://<your-bucket>/" --recursive
```

You should see objects under `02_intermediate/`, `03_primary/`, `04_feature/`, `06_models/`, and `08_reporting/`.

If the execution failed, see [Troubleshooting](#troubleshooting).

---

## Troubleshooting

<!-- vale off -->

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Runtime.InvalidEntrypoint` / `ProcessSpawnFailed` | Container image built for ARM (Apple Silicon) but Lambda runs x86_64 | Rebuild with `docker build --platform linux/amd64` and push again |
| `Could not find pyproject.toml` in `/var/task` | `bootstrap_project` called inside Lambda | Use `configure_project("<package_name>")` in `lambda_handler.py` as shown in Step 5 |
| `Dataset 'MatplotlibWriter' not found` | Outdated dataset type name in catalog | Use `matplotlib.MatplotlibDataset` (Kedro Datasets 3.x+) |
| `MemoryDataset` errors between nodes | Dataset not listed in `conf/aws/catalog.yml` | Add an S3-backed entry for every dataset shared across Lambda invocations |
| Step Functions times out | State machine timeout too short for your pipeline | Increase `timeout=Duration.minutes(...)` in `deploy.py` |
| Lambda out of memory | Default memory too low for modelling nodes | Increase `memory_size` in `deploy.py` (for example `1024` or higher) |
| `ModuleNotFoundError: No module named 'aws_cdk'` | CDK dependencies not installed in the Python env used by `cdk.json` | Install `deploy_requirements.txt` in that environment, or update `cdk.json` to point at the correct interpreter |

<!-- vale on -->

---

## Limitations

Each Lambda function has a [15-minute timeout](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html), a 10 GB memory limit, and a 10 GB container image size limit. If a node exceeds these limits, run it on another AWS service such as [AWS Batch](aws_batch.md) or [Amazon EMR Serverless](amazon_emr_serverless.md).

!!! warning "Image size with the full Spaceflights starter"
    The Spaceflights starter includes Jupyter, Viz, and reporting dependencies that increase image size. For production deployments, consider trimming `pyproject.toml` dependencies to what your pipeline requires.

---

## Further reading

### Kedro

- [Running Kedro in a distributed environment](../distributed.md)
- [Package a Kedro project](../package_a_project.md)
- [Run a packaged project](../package_a_project.md#run-a-packaged-project)
- [Catalog globals](https://docs.kedro.org/en/stable/configure/advanced_configuration.html#how-to-use-globals-and-runtime-params)
- [Lifecycle management with KedroSession](../../extend/session.md)

### AWS

- [AWS Lambda container images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [AWS CDK Python workshop](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [Creating an Amazon S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)
- [Creating an Amazon ECR repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html)
- [AWS Step Functions developer guide](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
