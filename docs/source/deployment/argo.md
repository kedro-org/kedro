# Argo Workflows (outdated documentation that needs review)

``` {important}
This page contains outdated documentation that has not been tested against recent Kedro releases. If you successfully use Argo Workflows with a recent version of Kedro, consider telling us the steps you took on [Slack](https://slack.kedro.org) or [GitHub](https://github.com/kedro-org/kedro/issues).
```

<div style="color:gray">This page explains how to convert your Kedro pipeline to use <a href="https://github.com/argoproj/argo-workflows">Argo Workflows</a>, an open-source container-native workflow engine for orchestrating parallel jobs on <a href="https://kubernetes.io/">Kubernetes</a>.


## Why would you use Argo Workflows?

We are interested in Argo Workflows, one of the 4 components of the Argo project. Argo Workflows is an open-source container-native workflow engine for orchestrating parallel jobs on Kubernetes.

Here are the main reasons to use Argo Workflows:

- It is cloud-agnostic and can run on any Kubernetes cluster
- It allows you to easily run and orchestrate compute intensive jobs in parallel on Kubernetes
- It manages the dependencies between tasks using a directed acyclic graph (DAG)

## Prerequisites

To use Argo Workflows, ensure you have the following prerequisites in place:

- [Argo Workflows is installed](https://github.com/argoproj/argo/blob/master/README.md#quickstart) on your Kubernetes cluster
- [Argo CLI is installed](https://github.com/argoproj/argo/releases) on your machine
- A `name` attribute is set for each Kedro {py:mod}`~kedro.pipeline.node` since it is used to build a DAG
- [All node input/output datasets must be configured in `catalog.yml`](../data/data_catalog_yaml_examples.md) and refer to an external location (e.g. AWS S3); you cannot use the `MemoryDataset` in your workflow

```{note}
Each node will run in its own container.
```

## How to run your Kedro pipeline using Argo Workflows

### Containerise your Kedro project

First, you need to containerise your Kedro project, using any preferred container solution (e.g. [`Docker`](https://www.docker.com/)), to build an image to use in Argo Workflows.

For the purpose of this walk-through, we are going to assume a `Docker` workflow. We recommend the [`Kedro-Docker`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin to streamline the process. [Instructions for Kedro-Docker are in the plugin's README.md](https://github.com/kedro-org/kedro-plugins/blob/main/README.md).

After you’ve built the Docker image for your project locally, [transfer the image to a container registry](./single_machine.md#how-to-use-container-registry).

### Create Argo Workflows spec

In order to build an Argo Workflows spec for your Kedro pipeline programmatically you can use the following Python script that should be stored in your project’s root directory:

```python
# <project_root>/build_argo_spec.py
import re
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

from kedro.framework.project import pipelines
from kedro.framework.startup import bootstrap_project

TEMPLATE_FILE = "argo_spec.tmpl"
SEARCH_PATH = Path("templates")


@click.command()
@click.argument("image", required=True)
@click.option("-p", "--pipeline", "pipeline_name", default=None)
@click.option("--env", "-e", type=str, default=None)
def generate_argo_config(image, pipeline_name, env):
    loader = FileSystemLoader(searchpath=SEARCH_PATH)
    template_env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
    template = template_env.get_template(TEMPLATE_FILE)

    project_path = Path.cwd()
    metadata = bootstrap_project(project_path)
    package_name = metadata.package_name

    pipeline_name = pipeline_name or "__default__"
    pipeline = pipelines.get(pipeline_name)

    tasks = get_dependencies(pipeline.node_dependencies)

    output = template.render(image=image, package_name=package_name, tasks=tasks)

    (SEARCH_PATH / f"argo-{package_name}.yml").write_text(output)


def get_dependencies(dependencies):
    deps_dict = [
        {
            "node": node.name,
            "name": clean_name(node.name),
            "deps": [clean_name(val.name) for val in parent_nodes],
        }
        for node, parent_nodes in dependencies.items()
    ]
    return deps_dict


def clean_name(name):
    return re.sub(r"[\W_]+", "-", name).strip("-")


if __name__ == "__main__":
    generate_argo_config()
```

The script accepts one required argument:

- `image`: image transferred to the container registry

You can also specify two optional arguments:

- `--pipeline`: pipeline name for which you want to build an Argo Workflows spec
- `--env`: Kedro configuration environment name, defaults to `local`

Add the following Argo Workflows spec template to `<project_root>/templates/argo_spec.tmpl`:

```jinja
{# <project_root>/templates/argo_spec.tmpl #}
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: {{ package_name }}-
spec:
  entrypoint: dag
  templates:
  - name: kedro
    metadata:
      labels:
        {# Add label to have an ability to remove Kedro Pods easily #}
        app: kedro-argo
    retryStrategy:
      limit: 1
    inputs:
      parameters:
      - name: kedro_node
    container:
      imagePullPolicy: Always
      image: {{ image }}
      env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              {# Secrets name #}
              name: aws-secrets
              key: access_key_id
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: aws-secrets
              key: secret_access_key
      command: [kedro]{% raw %}
      args: ["run", "-n",  "{{inputs.parameters.kedro_node}}"]
      {% endraw %}
  - name: dag
    dag:
      tasks:
      {% for task in tasks %}
      - name: {{ task.name }}
        template: kedro
        {% if task.deps %}
        dependencies:
        {% for dep in task.deps %}
          - {{ dep }}
        {% endfor %}
        {% endif %}
        arguments:
          parameters:
          - name: kedro_node
            value: {{ task.node }}
      {% endfor %}
```


```{note}
The Argo Workflows is defined as the dependencies between tasks using a directed-acyclic graph (DAG).
```

For the purpose of this walk-through, we will use an AWS S3 bucket for datasets; therefore `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables must be set to have an ability to communicate with S3. The `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` values should be stored in [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) (an example [Kubernetes Secrets spec is given below](#submit-argo-workflows-spec-to-kubernetes)).

The spec template is written with the [Jinja templating language](https://jinja.palletsprojects.com/en/2.11.x/), so you must install the Jinja Python package:

```console
$ pip install Jinja2
```

Finally, run the helper script from project's directory to build the Argo Workflows spec (the spec will be saved to `<project_root>/templates/argo-<package_name>.yml` file).

```console
$ cd <project_root>
$ python build_argo_spec.py <project_image>
```

### Submit Argo Workflows spec to Kubernetes

Before submitting the Argo Workflows spec you need to deploy a Kubernetes Secrets.

Here's an example Secrets spec:

```yaml
# secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: aws-secrets
data:
  access_key_id: <AWS_ACCESS_KEY_ID value encoded with base64>
  secret_access_key: <AWS_SECRET_ACCESS_KEY value encoded with base64>
type: Opaque
```

You can use the following command to encode AWS keys to base64:

```console
$ echo -n <original_key> | base64
```

Run the following commands to deploy the Kubernetes Secrets to the `default` namespace and check that it was created:

```console
$ kubectl create -f secret.yml
$ kubectl get secrets aws-secrets
```

Now, you are ready to submit the Argo Workflows spec as follows:

```console
$ cd <project_root>
$ argo submit --watch templates/argo-<package_name>.yml
```

```{note}
The Argo Workflows should be submitted to the same namespace as the Kubernetes Secrets. Please refer to the Argo CLI help to get more details about the usage.
```

In order to clean up your Kubernetes cluster you can use the following commands:

```console
$ kubectl delete pods --selector app=kedro-argo
$ kubectl delete -f secret.yml
```

### Kedro-Argo plugin

As an alternative, you can use [Kedro-Argo plugin](https://pypi.org/project/kedro-argo/) to convert a Kedro project to Argo Workflows.

```{warning}
The plugin is not supported by the Kedro team and we can't guarantee its workability.
```
</div>
