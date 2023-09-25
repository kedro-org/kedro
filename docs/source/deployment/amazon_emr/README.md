# EMR Serverless

[Amazon EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/emr-serverless.html) 
is utilized to manage and execute distributed computing workloads using Apache Spark. With its serverless architecture, 
it eliminates the need for provisioning or managing clusters to execute your Spark jobs. Instead, EMR Serverless 
independently allocates the necessary resources for each job and releases them once the job has been completed.

EMR Serverless is primarily employed when running pipelines that are either fully or partially dependent on PySpark. 
However, for other parts of the pipeline such as modeling, where a non-distributed computing approach may be suitable, EMR Serverless might not be a necessity.

**Contents:**
- [Context](#context)
- [Overview of Approach](#overview-of-approach)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [Infrastructure](#infrastructure)
    - [Create a private repository in ECR](#create-a-private-repository-in-ecr)
    - [Create an EMR Studio](#create-an-emr-studio)
    - [Create an application](#create-an-application)
  - [IAM](#iam)
    - [Create a job runtime role](#create-a-job-runtime-role)
    - [Grant access to ECR repository](#grant-access-to-ecr-repository)
  - [(Optional) Validate the custom image](#optional-validate-the-custom-image)
  - [Run a job](#run-a-job)
  - [FAQ](#faq)

## Context
Python applications on [Amazon Elastic MapReduce (EMR)](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html) 
have traditionally managed dependencies using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html). 
This can sometimes lead to complications due to script complexity, longer bootstrapping times, and potential inconsistencies 
across cluster instances. 

For our specific application, we have two primary requirements that necessitated 
a different approach:
- **Custom Python version:** By default, the latest EMR releases (6.10.0, 6.11.0) run Python 3.7, but our application requires Python 3.9 or later.
- **Python dependencies:** our application uses a range of third-party dependencies that need to be installed on both the driver and worker nodes.

Even though the official AWS documentation provides methods for configuring a [custom Python version](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html) 
and for [using custom dependencies](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python-libraries.html), these methods have some limitations. 
The outlined approach is prone to errors, can be difficult to debug, and does not ensure full compatibility with our needs (see the [FAQ](#faq) for more details).

With the advent of EMR Serverless and its support for [custom images](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html) (starting with Amazon EMR 6.9.0), we have a robust 
solution to overcome the outlined limitations. By using a custom Docker image, we can package our specific Python version along 
with all required dependencies into a single immutable container. This not only ensures a consistent runtime environment 
across our entire setup but also allows us to have better control over our runtime environment. 

Additionally, this approach helps to avoid job failures due to misconfigurations or potential conflicts with system-level packages, 
and ensures the package is portable 
enough to be debugged and tested locally (see more details on validation 
[here](#optional-validate-the-custom-image)). Hence, we can efficiently achieve a repeatable, reliable environment and improve our operational flexibility.

With this understanding of the challenges and the needs of our application, refer to the section below for an overview of how 
we approached this issue in our project.

## Overview of Approach

We create a custom image for EMR Serverless (see [Dockerfile](./Dockerfile)), to package dependencies and manage the runtime environment. More specifically:

- We package our Kedro project and install it on all EMR Serverless worker nodes. `kedro package` is used for this and the resultant `.whl` file is used for installation.
- We use a custom Python version instead of the default Python installed on EMR Serverless. [pyenv](https://github.com/pyenv/pyenv) is used for installing the custom Python version.
- Then, to run a job on EMR Serverless, we specify Spark properties to use the custom Python, and provide an [entrypoint script](./entrypoint.py) that accepts command line arguments for running Kedro.

For more details, refer to the following resources:
- [Package a Kedro project](https://docs.kedro.org/en/0.18.11/tutorial/package_a_project.html#package-a-kedro-project)
- [Run a packaged project](https://docs.kedro.org/en/0.18.11/tutorial/package_a_project.html#run-a-packaged-project)
- [Customizing an EMR Serverless image](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html)
- [Using custom images with EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-custom-images.html)

## Prerequisites
- Create an S3 bucket used to store data for EMR Serverless.

## Setup

### Infrastructure

#### Create a private repository in ECR

See details on how to do so [here](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html). 
You can use the default settings. This repository will be used to upload the EMR Serverless custom image.

#### Create an EMR Studio

To use EMR Serverless you need to create an EMR Studio.

- Go to the AWS Console > EMR > EMR Serverless. 
- Make sure you are in the correct region where you want to create your resource.
- Then, click "Get started" > "Create and launch EMR Studio".

#### Create an application 

- Type: Spark
- Release version: `emr-6.10.0`
- Architecture: `x86_64`
- Application setup options > "Choose custom settings"
- Custom image settings > "Use the custom image with this application"
- For simplicity, use the same custom image for both Spark drivers and executors
- Provide the ECR image URI; it must be located in the same region as the EMR Studio

You may customize other settings as required, or even change the release version and architecture options 
(along with making the changes in the custom image). 
However, this code base has only been tested with the above options.

See more details on creating an application [here](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/studio.html).

### IAM

#### Create a job runtime role

Follow the instructions under "Create a job runtime role" [here](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/getting-started.html).
This role will be used when submitting a job to EMR Serverless. The permissions defined in the policy also grant access 
to an S3 bucket (specify the S3 bucket you have created).

#### Grant access to ECR repository

Follow the steps below:
- Go to ECR in the AWS console.
- Click into the repository you created earlier, then on the left under Repositories > Permissions.
- Click "Edit policy JSON" and paste the policy specified
[here](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html) (under "Allow EMR Serverless to access the custom image repository"). 
- Make sure to enter the ARN for your EMR Serverless application in the `aws:SourceArn` value.

## (Optional) Validate the custom image

EMR Serverless provides a utility to validate your custom images locally, to make sure your modifications are still 
compatible to EMR Serverless and to prevent job failures. Refer to [Amazon EMR Serverless Image CLI](https://github.com/awslabs/amazon-emr-serverless-image-cli)
for more details on installation and using the tool.

## Run a job

**Important**:exclamation: On making changes to the custom image, and rebuilding and pushing to ECR, be sure to restart the EMR Serverless
application before submitting a job if your application is **already started**. Otherwise, new changes may not be reflected in the job run. 

This may be due to the fact that when the application has started, EMR Serverless keeps a pool of warm resources (also referred to as 
[pre-initialized capacity](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-capacity.html#pre-init-capacity))
ready to run a job, and the nodes may have already used the previous version of the ECR image.

---

See details on how to run a Spark job on EMR Serverless 
[here](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/jobs-spark.html).
The following parameters need to be provided:
- "entryPoint" - path to S3 where your [entrypoint script](./entrypoint.py) is uploaded.

**Note:** The use of an "entrypoint script" is necessitated by EMR Serverless' disregard for `[CMD]` or `[ENTRYPOINT]` instructions 
in the Dockerfile, as indicated in its [documentation](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html#considerations). 
Instead, running Kedro programmatically through an "entrypoint script" is preferred, eliminating the need to use, for example, 
a [subprocess](https://docs.python.org/3/library/subprocess.html) for invoking `kedro run`. See [FAQ](#faq) for more details.

- "entryPointArguments" - a list of arguments for running Kedro
- "sparkSubmitParameters" - set your properties to use the custom Python version


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

Enter the respective values in the placeholders above, e.g. use the ARN from the job runtime role created earlier for 
`<execution-role-arn>`.

## FAQ

#### 1. How is the approach defined here different from [this approach](https://kedro.org/blog/how-to-deploy-kedro-pipelines-on-amazon-emr) on the Kedro blog?

There are similarities in steps in both approaches. However, the key difference is we provide a custom Python version 
through the custom image, 
as opposed to only providing Python dependencies in a virtual environment for EMR to refer to.

It is also worth noting that currently, the approach of providing a custom image is only applicable to EMR Serverless. 
On EMR it would be worth exploring [using a custom AMI](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-custom-ami.html),
as an alternative to using [bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html).
However, this has not been explored nor tested in our current efforts.

#### 2. EMR Serverless already has Python installed. Why do we need a custom Python version?

Our code base is using Python 3.9 while the default Python installation on latest EMR releases (6.10.0, 6.11.0) is Python 3.7.

#### 3. Why do we need to create a custom image to provide the custom Python version? Can we not provide that using the virtual environment approach described [here](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html)?

We encountered difficulties while trying to follow this approach and also modifying it to use [pyenv](https://github.com/pyenv/pyenv) instead.
Specifically, while using [venv-pack](https://pypi.org/project/venv-pack/) we found this limitation, listed on their [documentation](https://jcristharif.com/venv-pack/#caveats) as well:
>Python is _not_ packaged with the environment, but rather symlinked in the environment. 
> This is useful for deployment situations where Python is already installed on the machine, but the required library dependencies may not be.

So, we face this error: `Too many levels of symbolic links`.

Additionally, we decided to go with the custom image approach because it neatly includes both installing our Kedro project and providing 
the custom Python version in one go. Alternatively, we would need to separately provide the files, and specify them as extra Spark configuration each time we submit a job.

#### 4. Why do we need to package the Kedro project and invoke using an entrypoint script? Why can't we just use [CMD] or [ENTRYPOINT] with `kedro run` in the custom image?

As mentioned in the [documentation](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/application-custom-image.html):
>EMR Serverless ignores `[CMD]` or `[ENTRYPOINT]` instructions in the Dockerfile. 

Additionally, we also prefer using the [entrypoint script](./entrypoint.py) approach to run Kedro 
programmatically, instead of e.g. using [subprocess](https://docs.python.org/3/library/subprocess.html) to invoke `kedro run`.

#### 5. How about using the method described in [Lifecycle management with KedroSession](https://docs.kedro.org/en/0.18.11/kedro_project_setup/session.html) to run Kedro programmatically?

This is indeed a valid alternative to run Kedro programmatically, without needing to package the Kedro project.
However, we found the caveat that the arguments are not a direct mapping to Kedro command line arguments:
- Different names are used e.g., "pipeline_name" and "node_names" are used here, as opposed to "pipeline" and "nodes".
- Different types are used e.g., to specify the "runner" you need to pass an `AbstractRunner` object, instead of a 
simple string value like "ThreadRunner".

Additionally, arguments need to be passed separately, e.g. "env" is passed directly to `KedroSession.create()` while 
other arguments such as "pipeline_name" and "node_names" need to be passed to `session.run()`.

Therefore, it is only straightforward for simple scenarios like invoking `kedro run`, or where you do not provide many command line arguments to Kedro.