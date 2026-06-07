# Amazon EMR Serverless

[Amazon EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/emr-serverless.html)
can be used to manage and execute distributed computing workloads using Apache Spark. Its serverless architecture eliminates the need to provision or manage clusters to execute your Spark jobs. Instead, EMR Serverless
independently allocates the resources needed for each job and releases them at completion.

EMR Serverless is typically used for pipelines that are either fully or partially dependent on PySpark.
For other parts of the pipeline such as modelling, where a non-distributed computing approach may be suitable, EMR Serverless might not be needed.


## Context
Python applications on [Amazon Elastic MapReduce (EMR)](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html)
have traditionally managed dependencies using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html).
This can sometimes lead to complications due to script complexity, longer bootstrapping times, and potential inconsistencies
across cluster instances.

Some applications may need a different approach, such as:

- **Custom Python version:** EMR Serverless base images may ship with a Python version older than your project needs. Kedro 1.x requires Python >=3.10, so a custom image is often required.
- **Python dependencies:** Some applications use a range of third-party dependencies that need to be installed on both the driver and worker nodes.

Even though the official AWS documentation provides methods for configuring a [custom Python version](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html)
and for [using custom dependencies](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python-libraries.html), there are some limitations. The methods are prone to errors, can be difficult to debug, and do not ensure full compatibility (see the [FAQ section below](#frequently-asked-questions) for more details).

EMR Serverless offers a solution to the limitations described, starting with Amazon EMR 6.9.0, which supports [custom images](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html). With a custom Docker image you can package a specific Python version along
with all required dependencies into a single immutable container. This ensures a consistent runtime environment
across the entire setup and also enables control over the runtime environment.

This approach helps to avoid job failures caused by configuration conflicts with system-level packages.
It also keeps the package portable so it can be debugged and tested locally ([see more details on validation](#optional-validate-the-custom-image)). Using the approach can provide a repeatable, reliable environment and improve operational flexibility.

With this context established, the rest of this page describes how to deploy a Kedro project to EMR Serverless.

## Overview of approach

This approach creates a custom Docker image for EMR Serverless to package dependencies and manage the runtime environment, and follows these steps:

- Packaging the Kedro project to install it on all EMR Serverless worker nodes. `kedro package` can be used for this: the resultant `.whl` file is used for installation, while `conf.tar.gz` contains the project configuration files.
- Using a custom Python version instead of the default Python installed on EMR Serverless. In the example, [pyenv](https://github.com/pyenv/pyenv) is used for installing the custom Python version. Choose any Python version **>=3.10** that matches your Kedro project's `requires-python` setting in `pyproject.toml`.
- Running a job on EMR Serverless specifying Spark properties. This is needed to use the custom Python and provide an entrypoint script that accepts command line arguments for running Kedro.

### Choose your Python version

Kedro 1.x supports **Python >=3.10**. When building the custom EMR image, set `PYTHON_VERSION` to the same patch release you use locally and declare in your project (for example `3.12.8`, `3.11.11`, or `3.10.16`). pyenv must support the exact patch release you choose.

Use the same value everywhere:

| Location | Example for Python 3.12.8 |
|----------|----------------------------|
| `pyproject.toml` | `requires-python = ">=3.10"` |
| Dockerfile `PYTHON_VERSION` | `3.12.8` |
| `sparkSubmitParameters` Python path | `/usr/.pyenv/versions/3.12.8/bin/python` |

#### Worked example: Python 3.12

If your Kedro project runs locally on **Python 3.12**, use `3.12.8` (or another 3.12 patch release supported by [pyenv](https://github.com/pyenv/pyenv)) consistently in the Dockerfile and job submission command.

In the Dockerfile:

```dockerfile
ENV PYTHON_VERSION=3.12.8
```

When submitting the job with the AWS CLI, set `sparkSubmitParameters` to:

```shell
--conf spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON=/usr/.pyenv/versions/3.12.8/bin/python \
--conf spark.emr-serverless.driverEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/3.12.8/bin/python \
--conf spark.executorEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/3.12.8/bin/python
```

??? example "Full AWS CLI example for Python 3.12.8"
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

Here is an example Dockerfile that can be used. Replace `<python-version>` with your chosen version (for example `3.12.8`). The EMR release in the `FROM` line must match the release label of your EMR Serverless application (see [AWS custom image guidance](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html)):

```dockerfile
FROM public.ecr.aws/emr-serverless/spark/emr-6.10.0:latest AS base

USER root

# Install Python build dependencies for pyenv
RUN yum install -y gcc make patch zlib-devel bzip2 bzip2-devel readline-devel \
        sqlite sqlite-devel openssl11-devel tk-devel libffi-devel xz-devel tar git

ENV PYENV_ROOT=/usr/.pyenv
ENV PATH=$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
ENV PYTHON_VERSION=<python-version>

# Install pyenv, then install and select the desired Python version (>=3.10)
RUN curl https://pyenv.run | bash && \
    export PYENV_ROOT="/usr/.pyenv" && \
    export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH" && \
    pyenv install ${PYTHON_VERSION} && \
    pyenv global ${PYTHON_VERSION}

# Copy and install packaged Kedro project
ENV KEDRO_PACKAGE=<PACKAGE_WHEEL_NAME>
COPY dist/$KEDRO_PACKAGE /tmp/dist/$KEDRO_PACKAGE
RUN pip install --upgrade pip && pip install /tmp/dist/$KEDRO_PACKAGE \
    && rm -f /tmp/dist/$KEDRO_PACKAGE

# Copy and extract conf folder
ADD dist/conf.tar.gz /home/hadoop/

# EMR Serverless runs the image as hadoop
USER hadoop:hadoop
```

Make sure to replace:

- `<python-version>` with a Python **>=3.10** release supported by pyenv (for example `3.12.8`, `3.11.11`, or `3.10.16`)
- `<PACKAGE_WHEEL_NAME>` with your own `.whl` file name

Run `kedro package` in your project root before building the image.
Here is the `entrypoint.py` entrypoint script:

```python
import sys
from <PACKAGE_NAME>.__main__ import main

main(sys.argv[1:])

```

Replace `<PACKAGE_NAME>` with your package name.

### Resources
For more details, see the following resources:

- [Package a Kedro project](../package_a_project.md#package-a-kedro-project)
- [Run a packaged project](../package_a_project.md#run-a-packaged-project)
- [Customising an EMR Serverless image](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html)
- [Using custom images with EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-custom-images.html)

## Setup

### Prerequisites

- A Kedro 1.x project with `requires-python = ">=3.10"` in `pyproject.toml`
- A local Python environment **>=3.10** matching the version you install in the custom image
- [Docker](https://www.docker.com/) installed locally to build the custom image
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) configured for your target region
- An S3 bucket to store data and job entrypoint scripts for EMR Serverless

### Infrastructure

1. **Create a private repository in ECR**. See details on how to do so [in the AWS documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html). You can use the default settings. This repository will be used to upload the EMR Serverless custom image.

2. **Create an EMR Studio**.

- Go to the AWS Console > EMR > EMR Serverless.
- Make sure you are in the correct region where you want to create your resource.
- Then, click "Get started" > "Create and launch EMR Studio".

3. **Create an application**.

- Type: Spark
- Release version: `emr-6.10.0` (must match the base image used in your Dockerfile)
- Architecture: `x86_64`
- Application setup options > "Choose custom settings"
- Custom image settings > "Use the custom image with this application"
- For simplicity, use the same custom image for both Spark drivers and executors
- Provide the ECR image URI; it must be located in the same region as the EMR Studio

You may customise other settings as required, or even change the release version and architecture options
(along with making the changes in the custom image).

```{warning}
The documented approach has only been tested with the above options.
```

See the AWS EMR Serverless documentation for [more details on creating an application](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/studio.html).

### IAM

1. **Create a job runtime role**. Follow the instructions under ["Create a job runtime role"](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/getting-started.html). This role will be used when submitting a job to EMR Serverless. The permissions defined in the policy also grant access
to an S3 bucket (specify the S3 bucket you have created).

2. **Grant access to ECR repository**.

- Go to ECR in the AWS console.
- Click into the repository you created earlier, then on the left under Repositories > Permissions.
- Click "Edit policy JSON" and paste [this policy](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html) under "Allow EMR Serverless to access the custom image repository".
- Make sure to enter the ARN for your EMR Serverless application in the `aws:SourceArn` value.

## (Optional) Validate the custom image

EMR Serverless provides a utility to validate your custom images locally, to make sure your modifications are still
compatible to EMR Serverless and to prevent job failures. See the [Amazon EMR Serverless Image CLI documentation](https://github.com/awslabs/amazon-emr-serverless-image-cli)
for more details.

## Run a job

!!! note
    When you change the custom image, rebuild it, and push it to ECR, restart the EMR Serverless application before submitting a job if the application is **already started**. Otherwise, the job may not pick up the new image.

    This behaviour occurs because a running application keeps a pool of warm resources (also referred to as [pre-initialised capacity](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/pre-init-capacity.html)) ready for jobs, and the nodes may already reference the previous version of the ECR image.

See details on [how to run a Spark job on EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/jobs-spark.html).

The following parameters need to be provided:
- "entryPoint" - the path to S3 where your `entrypoint.py` entrypoint script is uploaded.
- "entryPointArguments" - a list of arguments for running Kedro
- "sparkSubmitParameters" - set your properties to use the custom Python version

!!! note
    The use of an "entrypoint script" is needed because [EMR Serverless disregards `[CMD]` or `[ENTRYPOINT]` instructions
    in the Dockerfile](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html#considerations).
    We recommend running Kedro programmatically through an "entrypoint script" to avoid using, for example,
    separate process-spawning utilities from the Python standard library to invoke `kedro run`. See [FAQ](#frequently-asked-questions) for more details.


Example using AWS CLI:

```shell
aws emr-serverless start-job-run \
    --application-id <application-id> \
    --execution-role-arn <execution-role-arn> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "<s3-path-to-entrypoint-script>",
            "entryPointArguments": ["--env", "<emr-conf>", "--runner", "ThreadRunner", "--pipelines", "<kedro-pipeline-name>"],
            "sparkSubmitParameters": "--conf spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON=/usr/.pyenv/versions/<python-version>/bin/python --conf spark.emr-serverless.driverEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/<python-version>/bin/python --conf spark.executorEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/<python-version>/bin/python"
        }
    }'
```

Enter the respective values in the placeholders above. For example, use the ARN from the job runtime role created earlier for `<execution-role-arn>`. Use the same `<python-version>` value in `sparkSubmitParameters` as in the Dockerfile `PYTHON_VERSION`. See the [Python 3.12 worked example](#worked-example-python-312) above for a copy-paste ready command.

## Frequently asked questions

### How is the approach defined here different from the approach in ["Seven steps to deploy Kedro pipelines on Amazon EMR"](https://kedro.org/blog/how-to-deploy-kedro-pipelines-on-amazon-emr) on the Kedro blog?

There are similarities in steps in both approaches. The key difference is that this page explains how to provide a custom Python version
through the custom image. The blog post provides Python dependencies in a virtual environment for EMR.

The approach of providing a custom image applies to EMR *Serverless*. On EMR it would be worth considering [using a custom AMI](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-custom-ami.html), as an alternative to using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html). This has not been explored nor tested.

### Why install a custom Python version on EMR Serverless?

Some applications may need a different Python version than the default installation. Kedro 1.x requires Python >=3.10, while many EMR Serverless base images ship with an older Python version. Install whichever supported Python version (3.10, 3.11, 3.12, or newer) matches your Kedro project.

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
