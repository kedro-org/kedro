# Amazon EMR Serverless

[Amazon EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/emr-serverless.html)
can be used to manage and execute distributed computing workloads using Apache Spark. Its serverless architecture eliminates the need to provision or manage clusters to execute your Spark jobs. Instead, EMR Serverless
independently allocates the resources needed for each job and releases them at completion.

EMR Serverless is typically used for pipelines that are either fully or partially dependent on PySpark.
For other parts of the pipeline such as modeling, where a non-distributed computing approach may be suitable, EMR Serverless might not be needed.


## Context
Python applications on [Amazon Elastic MapReduce (EMR)](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html)
have traditionally managed dependencies using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html).
This can sometimes lead to complications due to script complexity, longer bootstrapping times, and potential inconsistencies
across cluster instances.

Some applications may need a different approach, such as:

- **Custom Python version:** By default, the latest EMR releases (6.10.0, 6.11.0) run Python 3.7, but an application may require Python 3.9 or later.
- **Python dependencies:** Some applications use a range of third-party dependencies that need to be installed on both the driver and worker nodes.

Even though the official AWS documentation provides methods for configuring a [custom Python version](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html)
and for [using custom dependencies](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python-libraries.html), there are some limitations. The methods are prone to errors, can be difficult to debug, and do not ensure full compatibility (see the [FAQ section below](#faq) for more details).

EMR Serverless offers a solution to the limitations described, starting with Amazon EMR 6.9.0, which supports [custom images](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html). With a custom Docker image you can package a specific Python version along
with all required dependencies into a single immutable container. This ensures a consistent runtime environment
across the entire setup and also enables control over the runtime environment.

This approach helps to avoid job failures due to misconfigurations or potential conflicts with system-level packages,
and ensures the package is portable so it can be debugged and tested locally ([see more details on validation](#optional-validate-the-custom-image)). Using the approach can provide a repeatable, reliable environment and improve operational flexibility.

With this context established, the rest of this page describes how to deploy a Kedro project to EMR Serverless.

## Overview of approach

This approach creates a custom Docker image for EMR Serverless to package dependencies and manage the runtime environment, and follows these steps:

- Packaging the Kedro project to install it on all EMR Serverless worker nodes. `kedro package` can be used for this: the resultant `.whl` file is used for installation, while `conf.tar.gz` contains the project configuration files.
- Using a custom Python version instead of the default Python installed on EMR Serverless. In the example, [pyenv](https://github.com/pyenv/pyenv) is used for installing the custom Python version.
- Running a job on EMR Serverless specifying Spark properties. This is needed to use the custom Python and provide an entrypoint script that accepts command line arguments for running Kedro.

Here is an example Dockerfile that can be used:

```shell
FROM public.ecr.aws/emr-serverless/spark/emr-6.10.0:latest AS base

USER root

# Install Python build dependencies for pyenv
RUN yum install -y gcc make patch zlib-devel bzip2 bzip2-devel readline-devel  \
        sqlite sqlite-devel openssl11-devel tk-devel libffi-devel xz-devel tar

# Install git for pyenv installation
RUN yum install -y git

# Add pyenv to PATH and set up environment variables
ENV PYENV_ROOT /usr/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
ENV PYTHON_VERSION=3.9.16

# Install pyenv, initialize it, install desired Python version and set as global
RUN curl https://pyenv.run | bash
RUN eval "$(pyenv init -)"
RUN pyenv install ${PYTHON_VERSION} && pyenv global ${PYTHON_VERSION}

# Copy and install packaged Kedro project
ENV KEDRO_PACKAGE <PACKAGE_WHEEL_NAME>
COPY dist/$KEDRO_PACKAGE /tmp/dist/$KEDRO_PACKAGE
RUN pip install --upgrade pip && pip install /tmp/dist/$KEDRO_PACKAGE  \
    && rm -f /tmp/dist/$KEDRO_PACKAGE

# Copy and extract conf folder
ADD dist/conf.tar.gz /home/hadoop/

# EMRS will run the image as hadoop
USER hadoop:hadoop
```

Make sure to replace `<PACKAGE_WHEEL_NAME>` with your own `.whl` file name.
Here is the `entrypoint.py` entrypoint script:

```python
import sys
from <PACKAGE_NAME>.__main__ import main

main(sys.argv[1:])

```

Replace `<PACKAGE_NAME>` with your package name.

### Resources
For more details, see the following resources:

- [Package a Kedro project](https://docs.kedro.org/en/stable/tutorial/package_a_project.html#package-a-kedro-project)
- [Run a packaged project](https://docs.kedro.org/en/stable/tutorial/package_a_project.html#run-a-packaged-project)
- [Customizing an EMR Serverless image](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html)
- [Using custom images with EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-custom-images.html)

## Setup

### Prerequisites
You must create an S3 bucket to store data for EMR Serverless.

### Infrastructure

1. **Create a private repository in ECR**. See details on how to do so [in the AWS documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html). You can use the default settings. This repository will be used to upload the EMR Serverless custom image.

2. **Create an EMR Studio**.

- Go to the AWS Console > EMR > EMR Serverless.
- Make sure you are in the correct region where you want to create your resource.
- Then, click "Get started" > "Create and launch EMR Studio".

3. **Create an application**.

- Type: Spark
- Release version: `emr-6.10.0`
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

```{note}
On making changes to the custom image, and rebuilding and pushing to ECR, be sure to restart the EMR Serverless
application before submitting a job if your application is **already started**. Otherwise, new changes may not be reflected in the job run.

This may be due to the fact that when the application has started, EMR Serverless keeps a pool of warm resources (also referred to as
[pre-initialized capacity](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/pre-init-capacity.html))
ready to run a job, and the nodes may have already used the previous version of the ECR image.
```

See details on [how to run a Spark job on EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/jobs-spark.html).

The following parameters need to be provided:
- "entryPoint" - the path to S3 where your `entrypoint.py` entrypoint script is uploaded.
- "entryPointArguments" - a list of arguments for running Kedro
- "sparkSubmitParameters" - set your properties to use the custom Python version

```{note}
The use of an "entrypoint script" is needed because [EMR Serverless disregards `[CMD]` or `[ENTRYPOINT]` instructions
in the Dockerfile](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html#considerations).
We recommend to run Kedro programmatically through an "entrypoint script" to eliminate the need to use, for example,
a [subprocess](https://docs.python.org/3/library/subprocess.html) to invoke `kedro run`. See [FAQ](#faq) for more details.
```


Example using AWS CLI:

```shell
aws emr-serverless start-job-run \
    --application-id <application-id> \
    --execution-role-arn <execution-role-arn> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "<s3-path-to-entrypoint-script>",
            "entryPointArguments": ["--env", "<emr-conf>", "--runner", "ThreadRunner", "--pipeline", "<kedro-pipeline-name>"],
            "sparkSubmitParameters": "--conf spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON=/usr/.pyenv/versions/3.9.16/bin/python --conf spark.emr-serverless.driverEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/3.9.16/bin/python --conf spark.executorEnv.PYSPARK_PYTHON=/usr/.pyenv/versions/3.9.16/bin/python"
        }
    }'
```

Enter the respective values in the placeholders above. For example, use the ARN from the job runtime role created earlier for `<execution-role-arn>`.

## FAQ

### How is the approach defined here different from the approach in ["Seven steps to deploy Kedro pipelines on Amazon EMR"](https://api/kedro.org/blog/how-to-deploy-kedro-pipelines-on-amazon-emr) on the Kedro blog?

There are similarities in steps in both approaches. The key difference is that this page explains how to provide a custom Python version
through the custom image. The blog post provides Python dependencies in a virtual environment for EMR.

The approach of providing a custom image applies to EMR *Serverless*. On EMR it would be worth considering [using a custom AMI](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-custom-ami.html), as an alternative to using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html). This has not been explored nor tested as yet.

### EMR Serverless already has Python installed. Why do we need a custom Python version?

Some applications may require a different Python version than the default version installed. For example, your code base may require Python 3.9 while the default Python installation on the latest EMR releases (6.10.0, 6.11.0) is based on Python 3.7.

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

### How about using the method described in [Lifecycle management with KedroSession](https://docs.kedro.org/en/0.18.11/kedro_project_setup/session.html) to run Kedro programmatically?

This is a valid alternative to run Kedro programmatically, without needing to package the Kedro project, but the arguments are not a direct mapping to Kedro command line arguments:
- Different names are used. For example, "pipeline_name" and "node_names" are used instead of "pipeline" and "nodes".
- Different types are used. For example, to specify the "runner" you need to pass an `AbstractRunner` object, instead of a string value like "ThreadRunner".

Arguments need to be passed separately: "env" is passed directly to `KedroSession.create()` while
other arguments such as "pipeline_name" and "node_names" need to be passed to `session.run()`.

It is most suited to scenarios such as invoking `kedro run`, or where you do not provide many command line arguments to Kedro.
