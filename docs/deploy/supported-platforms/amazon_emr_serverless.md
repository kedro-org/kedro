# Amazon EMR Serverless

[Amazon EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/emr-serverless.html)
can be used to manage and execute distributed computing workloads using Apache Spark. Its serverless architecture eliminates the need to provision or manage clusters to execute your Spark jobs. Instead, EMR Serverless
independently allocates the resources needed for each job and releases them at completion.

EMR Serverless is typically used for pipelines that are either fully or partially dependent on PySpark.
For other parts of the pipeline such as modelling, where a non-distributed computing approach may be suitable, EMR Serverless might not be needed.

## Compatibility

This guide documents deployment of **Kedro 1.x** on **EMR Serverless 7.x**, which is the recommended release line for new projects. Kedro requires Python >=3.10; EMR 7.x default Python (~3.9) is still below that threshold, so a **custom image** with Python >=3.10 is required.

| | **EMR 7.x (recommended)** | **EMR 6.x (legacy)** |
|--|---------------------------|----------------------|
| Kedro version | 1.x | 1.x |
| EMR release (example) | `emr-7.13.0` | `emr-6.10.0` |
| Base image | `public.ecr.aws/emr-serverless/spark/emr-7.13.0:latest` | `public.ecr.aws/emr-serverless/spark/emr-6.10.0:latest` |
| Base OS | Amazon Linux 2023 | Amazon Linux 2 |
| Python install | `dnf` (for example `python3.12`) | [pyenv](https://github.com/pyenv/pyenv) |
| Spark Python path (example) | `/usr/bin/python3.12` | `/usr/.pyenv/versions/3.12.8/bin/python` |

!!! warning "Legacy: EMR 6.x"
    EMR 6.x ships with Python ~3.7 by default. Python 3.10+ requires pyenv or a custom compile in your image, which is more complex than EMR 7.x. We do **not** recommend EMR 6.x for new Kedro 1.x deployments. If you are constrained to EMR 6.x, see [Legacy: EMR 6.x](#legacy-emr-6x).

Keep the EMR release label aligned everywhere: the Dockerfile `FROM` line, EMR Serverless application release, `validate-image -r` flag, and job submission must all match (for example `emr-7.13.0` or `emr-6.10.0`).

## Context
Python applications on [Amazon Elastic MapReduce (EMR)](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html)
have traditionally managed dependencies using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html).
This can sometimes lead to complications due to script complexity, longer bootstrapping times, and potential inconsistencies
across cluster instances.

Some applications may need a different approach, such as:

- **Custom Python version:** EMR Serverless base images ship with a Python version below Kedro 1.x requirements. Kedro requires Python >=3.10, so a custom image is required.
- **Python dependencies:** Some applications use a range of third-party dependencies that need to be installed on both the driver and worker nodes.

Even though the official AWS documentation provides methods for configuring a [custom Python version](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html)
and for [using custom dependencies](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python-libraries.html), there are some limitations. The methods are prone to errors, can be difficult to debug, and do not ensure full compatibility (see the [FAQ section below](#frequently-asked-questions) for more details).

EMR Serverless supports [custom images](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html) (from EMR 6.9.0 onwards). With a custom Docker image you can package a specific Python version along
with all required dependencies into a single immutable container. This ensures a consistent runtime environment
across the entire setup and also enables control over the runtime environment.

This approach helps to avoid job failures caused by configuration conflicts with system-level packages.
It also keeps the package portable so it can be debugged and tested locally ([see more details on validation](#validate-the-custom-image)). Using the approach can provide a repeatable, reliable environment and improve operational flexibility.

With this context established, the rest of this page describes how to deploy a Kedro project to EMR Serverless 7.x. See [Legacy: EMR 6.x](#legacy-emr-6x) if you cannot use EMR 7.x.

## Overview of approach

This approach creates a custom Docker image for EMR Serverless to package dependencies and manage the runtime environment, and follows these steps:

1. **Package the Kedro project** with `kedro package` so worker nodes can install the `.whl` file; `conf.tar.gz` contains project configuration.
2. **Install Python >=3.10** in the custom image (with `dnf` on EMR 7.x, or pyenv on EMR 6.x).
3. **Run a job on EMR Serverless** with Spark properties that point to your custom Python, and an S3 entrypoint script that invokes Kedro.

## Prerequisites

- A Kedro 1.x project with `requires-python = ">=3.10"` in `pyproject.toml`
- A local Python environment **>=3.10** matching the version you install in the custom image
- [Docker](https://www.docker.com/) installed locally to build the custom image
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) configured for your target region
- An S3 bucket to store data and job entrypoint scripts for EMR Serverless
- An EMR Serverless application on **7.x** (recommended) or **6.x** (legacy), with a release label that matches your Dockerfile

## Choose your Python version

Kedro 1.x supports **Python >=3.10**. Install the same version locally, in your Docker image, and in Spark configuration. The [working example](#emr-7x-working-example) below uses **Python 3.12**.

## Package the Kedro project

Run the following in your project root before building the Docker image:

```bash
kedro package
```

This creates a `.whl` file and `conf.tar.gz` in the `dist/` folder. See [Package a Kedro project](../package_a_project.md#package-a-kedro-project) for details.

## Working example

Replace the placeholders below before building and submitting jobs:

- `<PACKAGE_WHEEL_NAME>` — wheel file name from `dist/` (for example `spaceflights-0.1-py3-none-any.whl`)
- `<PACKAGE_NAME>` — Python package name (for example `spaceflights`)
- `<emr-conf>` — Kedro config environment (for example `emr`)
- `<kedro-pipeline-name>` — pipeline to run (for example `__default__`)
- `<s3-path-to-entrypoint-script>` — S3 URI to `entrypoint.py`
- `<application-id>` and `<execution-role-arn>` — from your EMR Serverless application and IAM role

### EMR 7.x working example

Recommended for new Kedro 1.x deployments. Uses **`emr-7.13.0`**, **Python 3.12** via `dnf`, and Amazon Linux 2023.

**Dockerfile**

```dockerfile
FROM public.ecr.aws/emr-serverless/spark/emr-7.13.0:latest AS base

USER root

RUN dnf install -y python3.12 python3.12-pip

ENV KEDRO_PACKAGE=<PACKAGE_WHEEL_NAME>
COPY dist/$KEDRO_PACKAGE /tmp/dist/$KEDRO_PACKAGE
RUN python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install /tmp/dist/$KEDRO_PACKAGE && \
    rm -f /tmp/dist/$KEDRO_PACKAGE

ADD dist/conf.tar.gz /home/hadoop/

USER hadoop:hadoop
```

**Validate the image**

```bash
docker build -t kedro-emr-7 .
pip install amazon-emr-serverless-image-cli
amazon-emr-serverless-image validate-image -i kedro-emr-7 -r emr-7.13.0 -t spark
```

**Create the EMR Serverless application**

- Release version: `emr-7.13.0`
- Custom image: your ECR image URI built from the Dockerfile above

**Submit a job**

```shell
aws emr-serverless start-job-run \
    --application-id <application-id> \
    --execution-role-arn <execution-role-arn> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "<s3-path-to-entrypoint-script>",
            "entryPointArguments": ["--env", "<emr-conf>", "--runner", "ThreadRunner", "--pipelines", "<kedro-pipeline-name>"],
            "sparkSubmitParameters": "--conf spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON=/usr/bin/python3.12 --conf spark.emr-serverless.driverEnv.PYSPARK_PYTHON=/usr/bin/python3.12 --conf spark.executorEnv.PYSPARK_PYTHON=/usr/bin/python3.12"
        }
    }'
```

## Build the custom Docker image

See [EMR 7.x working example](#emr-7x-working-example) for the complete Dockerfile, or [Legacy: EMR 6.x](#legacy-emr-6x) for EMR 6.x. The EMR release in the `FROM` line must match your EMR Serverless application release label. See [AWS custom image guidance](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html).

Build and push the image to your private ECR repository after replacing the placeholders.

## Entrypoint script

Upload an `entrypoint.py` script to S3 and reference it as the Spark `entryPoint`. EMR Serverless ignores `[CMD]` and `[ENTRYPOINT]` in the Dockerfile, so this script is required.

```python
import sys
from <PACKAGE_NAME>.__main__ import main

main(sys.argv[1:])
```

Replace `<PACKAGE_NAME>` with your package name. The `entryPointArguments` passed at job submission time are forwarded to `main()` as CLI arguments (for example `--env`, `--pipelines`, `--runner`).

See the [KedroSession FAQ](#how-about-using-the-method-described-in-lifecycle-management-with-kedrosession) if you prefer the session API over `__main__`.

### Resources

- [Package a Kedro project](../package_a_project.md#package-a-kedro-project)
- [Run a packaged project](../package_a_project.md#run-a-packaged-project)
- [EMR Serverless 7.13.0 release notes](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/release-version-7130.html)
- [Customising an EMR Serverless image](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html)
- [Using custom images with EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-custom-images.html)

## Setup

### Infrastructure

1. **Create a private repository in ECR**. See [the AWS documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html). This repository stores your custom EMR Serverless image.

2. **Create an EMR Studio**.

    - Go to the AWS Console > EMR > EMR Serverless.
    - Make sure you are in the correct region.
    - Click "Get started" > "Create and launch EMR Studio".

3. **Create an application**.

    - Type: Spark
    - Release version: `emr-7.13.0` (must match the base image in your Dockerfile; see [EMR 7.x working example](#emr-7x-working-example))
    - Architecture: `x86_64`
    - Application setup options > "Choose custom settings"
    - Custom image settings > "Use the custom image with this application"
    - For simplicity, use the same custom image for both Spark drivers and executors
    - Provide the ECR image URI in the same region as the EMR Studio

See the AWS EMR Serverless documentation for [more details on creating an application](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/studio.html).

### IAM

1. **Create a job runtime role**. Follow ["Create a job runtime role"](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/getting-started.html). This role is used when submitting jobs and should grant access to your S3 bucket.

2. **Grant access to the ECR repository**.

    - Go to ECR in the AWS console.
    - Open your repository > Repositories > Permissions.
    - Click "Edit policy JSON" and paste [this policy](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html) under "Allow EMR Serverless to access the custom image repository".
    - Enter your EMR Serverless application ARN in the `aws:SourceArn` value.

## Validate the custom image

EMR Serverless provides a utility to validate custom images locally before deployment. See the [Amazon EMR Serverless Image CLI](https://github.com/awslabs/amazon-emr-serverless-image-cli) and the validate command in [EMR 7.x working example](#emr-7x-working-example).

## Run a job

!!! note
    When you change the custom image, rebuild it, and push it to ECR, restart the EMR Serverless application before submitting a job if the application is **already started**. Otherwise, the job may not pick up the new image.

    This behaviour occurs because a running application keeps a pool of warm resources (also referred to as [pre-initialised capacity](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/pre-init-capacity.html)) ready for jobs, and the nodes may already reference the previous version of the ECR image.

See [how to run a Spark job on EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/jobs-spark.html).

Provide the following in your job driver:

- **entryPoint** — S3 path to your `entrypoint.py` script
- **entryPointArguments** — Kedro CLI arguments
- **sparkSubmitParameters** — Python paths for your custom interpreter

See [EMR 7.x working example](#emr-7x-working-example) for a complete `aws emr-serverless start-job-run` command, or [Legacy: EMR 6.x](#legacy-emr-6x) for EMR 6.x. Use the ARN from the job runtime role for `<execution-role-arn>`.

## Frequently asked questions

### Should I use EMR 6.x or 7.x with Kedro 1.x?

Use **EMR 7.x** for all new Kedro 1.x deployments. EMR 7.x (Amazon Linux 2023) lets you install Python >=3.10 with `dnf` in a custom image. EMR 6.x defaults to Python ~3.7; reaching Python 3.10+ requires pyenv or a custom compile on Amazon Linux 2, which is harder to build and maintain. See [Legacy: EMR 6.x](#legacy-emr-6x) only if your organisation cannot move to EMR 7.x.

### How is the approach defined here different from the approach in ["Seven steps to deploy Kedro pipelines on Amazon EMR"](https://kedro.org/blog/how-to-deploy-kedro-pipelines-on-amazon-emr) on the Kedro blog?

There are similarities in steps in both approaches. The key difference is that this page explains how to provide a custom Python version
through the custom image. The blog post provides Python dependencies in a virtual environment for EMR.

The approach of providing a custom image applies to EMR *Serverless*. On EMR it would be worth considering [using a custom AMI](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-custom-ami.html), as an alternative to using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html). This has not been explored nor tested.

### Why install a custom Python version on EMR Serverless?

Kedro 1.x requires Python >=3.10. EMR 7.x defaults to ~3.9, so a custom image with Python >=3.10 is still required even on the recommended release line.

### Why do we need to create a custom image to provide the custom Python version?

You may encounter difficulties with the [virtual environment approach](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html) when modifying it to use [pyenv](https://github.com/pyenv/pyenv). While using [venv-pack](https://pypi.org/project/venv-pack/) we found [a limitation that returned the error `Too many levels of symbolic links`](https://jcristharif.com/venv-pack/#caveats), which is documented as follows:

>Python is _not_ packaged with the environment, but rather symlinked in the environment.
> This is useful for deployment situations where Python is already installed on the machine, but the required library dependencies may not be.

The custom image approach includes both installing the Kedro project and provides
the custom Python version in one go. Otherwise, you would need to separately provide the files, and specify them as extra Spark configuration each time you submit a job.

### Why do we need to package the Kedro project and invoke using an entrypoint script? Why can't we use [CMD] or [ENTRYPOINT] with `kedro run` in the custom image?

As mentioned in the [AWS documentation](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html), EMR Serverless ignores `[CMD]` or `[ENTRYPOINT]` instructions in the Dockerfile.

We recommend using the `entrypoint.py` entrypoint script approach to run Kedro
programmatically, instead of using [subprocess](https://docs.python.org/3/library/subprocess.html) to invoke `kedro run`.

### How about using the method described in [Lifecycle management with KedroSession](../../extend/session.md) to run Kedro programmatically?

You can run Kedro with `KedroSession` inside your Spark `entrypoint.py` script instead of calling your packaged project's `__main__` module. You still package the project and install the wheel in the custom image as described above; the session API is an alternative way to *invoke* the pipeline from the entrypoint script.

The session API does not mirror the CLI one-to-one. The table below shows the main differences:

| CLI flag | `KedroSession` API | Method |
|----------|-------------------|--------|
| `--env` | `env` | `KedroSession.create()` |
| `--params` | `runtime_params` | `KedroSession.create()` |
| `--conf-source` | `conf_source` | `KedroSession.create()` |
| `--pipelines` | `pipeline_names` (a list of strings) | `session.run()` |
| `--nodes` | `node_names` | `session.run()` |
| `--runner` | `runner` (an `AbstractRunner` instance, for example `ThreadRunner()`) | `session.run()` |
| `--tags` | `tags` | `session.run()` |
| `--from-nodes` / `--to-nodes` | `from_nodes` / `to_nodes` | `session.run()` |
| `--load-versions` | `load_versions` | `session.run()` |

In a packaged EMR deployment, call `configure_project()` (not `bootstrap_project()`) before creating the session. Here is an example entrypoint script:

```python
from kedro.framework.project import configure_project
from kedro.framework.session import KedroSession
from kedro.runner import ThreadRunner

configure_project("<PACKAGE_NAME>")

with KedroSession.create(env="<emr-conf>") as session:
    session.run(
        pipeline_names=["<kedro-pipeline-name>"],
        runner=ThreadRunner(),
    )
```

Upload this script to S3 and reference it as the Spark `entryPoint`, the same way as the `__main__`-based entrypoint described earlier.

**When to use which approach:**

- Use the **`__main__` entrypoint** (passing `entryPointArguments` such as `--env`, `--pipelines`, and `--runner`) when you want the same interface as `python -m <package_name>` or `kedro run` at the command line.
- Use **`KedroSession`** when you prefer explicit Python control over run options, or when you do not want to translate CLI arguments into `entryPointArguments`.

We still recommend avoiding [subprocess](https://docs.python.org/3/library/subprocess.html) to shell out to `kedro run` from the entrypoint script.

## Legacy: EMR 6.x

!!! warning
    This section is for teams that cannot migrate to EMR 7.x. EMR 6.x is built on Amazon Linux 2 and ships with Python ~3.7 by default. Python 3.10+ requires [pyenv](https://github.com/pyenv/pyenv) or a custom compile in your image. Custom images require EMR **6.9.0** or later.

Follow the main guide for shared steps (packaging, entrypoint script, IAM, and ECR setup). Replace the Dockerfile, validation command, application release, and job submission below.

### EMR 6.x working example

Uses **`emr-6.10.0`**, **Python 3.12.8** via pyenv, and Amazon Linux 2.

**Dockerfile**

```dockerfile
FROM public.ecr.aws/emr-serverless/spark/emr-6.10.0:latest AS base

USER root

RUN yum install -y gcc make patch zlib-devel bzip2 bzip2-devel readline-devel \
        sqlite sqlite-devel openssl11-devel tk-devel libffi-devel xz-devel tar git

ENV PYENV_ROOT=/usr/.pyenv
ENV PATH=$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
ENV PYTHON_VERSION=3.12.8

RUN curl https://pyenv.run | bash && \
    export PYENV_ROOT="/usr/.pyenv" && \
    export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH" && \
    pyenv install ${PYTHON_VERSION} && \
    pyenv global ${PYTHON_VERSION}

ENV KEDRO_PACKAGE=<PACKAGE_WHEEL_NAME>
COPY dist/$KEDRO_PACKAGE /tmp/dist/$KEDRO_PACKAGE
RUN pip install --upgrade pip && pip install /tmp/dist/$KEDRO_PACKAGE \
    && rm -f /tmp/dist/$KEDRO_PACKAGE

ADD dist/conf.tar.gz /home/hadoop/

USER hadoop:hadoop
```

**Validate the image**

```bash
docker build -t kedro-emr-6 .
pip install amazon-emr-serverless-image-cli
amazon-emr-serverless-image validate-image -i kedro-emr-6 -r emr-6.10.0 -t spark
```

**Create the EMR Serverless application**

- Release version: `emr-6.10.0`
- Custom image: your ECR image URI built from the Dockerfile above

**Submit a job**

```shell
aws emr-serverless start-job-run \
    --application-id <application-id> \
    --execution-role-arn <execution-role-arn> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "<s3-path-to-entrypoint-script>",
            "entryPointArguments": ["--env", "<emr-conf>", "--runner", "ThreadRunner", "--pipelines", "<kedro-pipeline-name>"],
            "sparkSubmitParameters": "--conf spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON=/usr/.pyenv/versions/3.12.8/bin/python --conf spark.emr-serverless.driverEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/3.12.8/bin/python --conf spark.executorEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/3.12.8/bin/python"
        }
    }'
```

If you change `PYTHON_VERSION` in the Dockerfile, update the paths in `sparkSubmitParameters` to match.

See [AWS custom Python version samples](https://github.com/aws-samples/emr-serverless-samples/tree/main/examples/pyspark/custom_python_version) for additional EMR 6.x context.
