# AWS Step Functions

This guide explains how to deploy a Kedro project with [AWS Step Functions](https://aws.amazon.com/step-functions/) so each pipeline node runs as an [AWS Lambda](https://aws.amazon.com/lambda/) function, orchestrated by a Step Functions state machine.

## What you will do

You will take the [Spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas/) project and configure datasets on Amazon S3. You will package the pipeline into a Lambda container image and deploy it with the [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/) v2. The result is a state machine that runs the full `__default__` pipeline end to end.

The deployed state machine looks like this in the AWS Management Console:

![](../../meta/images/aws_step_functions_state_machine.png)

## Strategy

Each Kedro node becomes a Lambda function that shares the same container image. Step Functions runs nodes in parallel within each dependency group and sequentially across groups, following the same principles as [running Kedro in a distributed environment](../distributed.md).

Because Lambda functions are isolated, every dataset that crosses node boundaries must use persistent storage (for example S3). `MemoryDataset` entries cannot be shared between functions.

## Prerequisites

Before you start, make sure you have:

- An [AWS account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/) and [configured AWS credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) on your machine
- [Docker](https://docs.docker.com/get-docker/) (or [Podman](https://podman.io/) with a `docker` alias) to build container images
- [Node.js](https://nodejs.org/) and the CDK CLI — see the [AWS CDK installation guide](https://docs.aws.amazon.com/cdk/v2/guide/cli.html):

```console
$ npm install -g aws-cdk
$ cdk --version
```

- A Kedro project generated from the Spaceflights starter (Kedro 1.x):

```console
$ kedro new -s spaceflights-pandas -n spaceflights_step_functions
```

Name the project directory `spaceflights-step-functions`. Complete the [Spaceflights tutorial](../../tutorials/spaceflights_tutorial.md) if you are new to the project layout.


## Step 1. Run the pipeline locally

From the project root, install dependencies and run the pipeline:

```console
$ pip install -e .
$ kedro run
```

**Checkpoint:** the pipeline completes without errors.

## Step 2. Create an S3 bucket and upload raw data

Create a globally unique bucket and upload the raw datasets. Replace `<your-bucket>` with your bucket name throughout the rest of this guide.

```shell
export AWS_REGION=<your-aws-region>
export S3_BUCKET=<your-bucket>

aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"
aws s3 sync data/01_raw/ "s3://${S3_BUCKET}/01_raw/"
```

See the [AWS documentation on creating S3 buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html) for more details.

**Checkpoint:** `aws s3 ls "s3://${S3_BUCKET}/01_raw/"` lists `companies.csv`, `reviews.csv`, and `shuttles.xlsx`.

## Step 3. Add an `aws` configuration environment

Create `conf/aws/` with a `globals.yml` file and a `catalog.yml` that points every dataset to S3. Use [catalog globals](https://docs.kedro.org/en/stable/configure/advanced_configuration.html#how-to-use-globals-and-runtime-params) so the bucket name is defined in one place.

`conf/aws/globals.yml`:

```yaml
s3_bucket: <your-bucket>
```

Add `s3fs` to your project dependencies in `pyproject.toml`:

```toml
"s3fs>=2024.6.0"
```

The `aws` catalog must override every dataset used by the deployed pipeline, including intermediate outputs such as `X_train` and reporting artefacts. The Spaceflights starter uses Parquet for intermediate tables and includes a reporting pipeline.

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

**Checkpoint:** `kedro run --env aws` completes and writes outputs to S3.

## Step 4. Package the Kedro project

Package the project as a Python wheel. See [Package a Kedro project](../package_a_project.md) for details.

```console
$ kedro package
```

This creates `dist/spaceflights_step_functions-0.1-py3-none-any.whl` (the exact filename depends on your package version).

## Step 5. Create the Lambda handler

Create `lambda_handler.py` in the project root. Each Lambda invocation runs a single node named in the event payload. The handler uses `configure_project` because the packaged wheel is installed into the container rather than the full project tree.

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

## Step 6. Build the Lambda container image

Create a `Dockerfile` to define the custom Docker image or an available base image to act as the base for our Lambda functions, here we used [AWS Lambda Python 3.12 base image](https://gallery.ecr.aws/lambda/python):

```Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY conf/ ${LAMBDA_TASK_ROOT}/conf/

COPY dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl --target "${LAMBDA_TASK_ROOT}" \
    && rm -f /tmp/*.whl

CMD ["lambda_handler.handler"]
```

Build the image and push it to [Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html). On Apple Silicon Macs, build for the `linux/amd64` platform because Lambda functions run on x86_64 by default.

```shell
export AWS_ACCOUNT_ID=<your-aws-account-id>
export AWS_REGION=<your-aws-region>
export ECR_REPO=spaceflights-step-functions
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

# Create the ECR repository — see https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html
aws ecr create-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}"

docker build --platform linux/amd64 -t "${ECR_REPO}:latest" .
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker tag "${ECR_REPO}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"
```

**Checkpoint:** `aws ecr describe-images --repository-name "${ECR_REPO}"` shows the `latest` tag.

## Step 7. Write the CDK deployment script

Install CDK Python dependencies into the same environment as your Kedro project:

`deploy_requirements.txt`:

```
aws-cdk-lib>=2.170.0
constructs>=10.0.0
```

```console
$ pip install -r deploy_requirements.txt
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

Use the same Python environment for `deploy.py` that has both Kedro and `aws-cdk-lib` installed. If your system `python3` differs from the environment where you installed dependencies, point `app` at that interpreter (for example `.venv/bin/python deploy.py`).

## Step 8. Deploy with CDK

Bootstrap CDK in your account (first time per account/region) and deploy the stack:

```shell
cdk bootstrap "aws://<your-aws-account-id>/<your-aws-region>"
cdk deploy
```

After deployment, open the [Step Functions console](https://console.aws.amazon.com/states/) to see the state machine:

![](../../meta/images/aws_step_functions_state_machine_listing.png)

You will also see one Lambda function per Kedro node:

![](../../meta/images/aws_lambda_functions.png)

**Checkpoint:** the CloudFormation stack `KedroStepFunctionsStack` reaches `CREATE_COMPLETE`.

## Step 9. Run the state machine

Start an execution from the Step Functions console, or with the AWS CLI:

```shell
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name, 'spaceflights')].stateMachineArn | [0]" \
  --output text)

aws stepfunctions start-execution \
  --state-machine-arn "${STATE_MACHINE_ARN}" \
  --name "kedro-run-$(date +%s)"
```

**Checkpoint:** the execution status is `SUCCEEDED`.

## Step 10. Verify outputs on S3

Confirm that intermediate and final datasets were written:

```shell
aws s3 ls "s3://${S3_BUCKET}/" --recursive
```

You should see objects under `02_intermediate/`, `03_primary/`, `04_feature/`, `06_models/`, and `08_reporting/`.

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

<!-- vale on -->

## Limitations

Each Lambda function has a [15-minute timeout](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html), a 10 GB memory limit, and a 10 GB container image size limit. If a node exceeds these limits, run it on another AWS service such as [AWS Batch](aws_batch.md) or [Amazon EMR Serverless](amazon_emr_serverless.md).

The Spaceflights starter includes Jupyter, Viz, and reporting dependencies that increase image size. For production deployments, consider trimming `pyproject.toml` dependencies to what your pipeline requires.

## Further reading

### Kedro

- [Running Kedro in a distributed environment](../distributed.md)
- [Package a Kedro project](../package_a_project.md)
- [Run a packaged project](../package_a_project.md#run-a-packaged-project)
- [Catalog globals](https://docs.kedro.org/en/stable/configure/advanced_configuration.html#how-to-use-globals-and-runtime-params)

### AWS

- [AWS Lambda container images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [AWS CDK Python workshop](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [Creating an Amazon S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)
- [Creating an Amazon ECR repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html)
- [AWS Step Functions developer guide](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
