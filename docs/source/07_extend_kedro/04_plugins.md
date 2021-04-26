# Kedro plugins


> *Note:* This documentation is based on `Kedro 0.17.1`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

Kedro plugins allow you to create new features for Kedro and inject additional commands into the CLI. Plugins are developed as separate Python packages that exist outside of any Kedro project.

## Overview

Kedro uses [`setuptools`](https://setuptools.readthedocs.io/en/latest/setuptools.html), which is a collection of enhancements to the Python `distutils` to allow developers to build and distribute Python packages. Kedro uses various entry points in [`pkg_resources`](https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins) to provide plugin functionality.

## Example of a simple plugin

Here is a simple example of a plugin that prints the pipeline as JSON:

`kedrojson/plugin.py`

```python
import click
from kedro.framework.session import KedroSession


@click.group(name="JSON")
def commands():
    """ Kedro plugin for printing the pipeline in JSON format """
    pass


@commands.command()
@click.pass_obj
def to_json(metadata):
    """ Display the pipeline in JSON format """
    session = KedroSession.create(metadata.package_name)
    context = session.load_context()
    print(context.pipeline.to_json())
```

The plugin provides the following `entry_points` config in `setup.py`:

```python
setup(
    entry_points={"kedro.project_commands": ["kedrojson = kedrojson.plugin:commands"],}
)
```

Once the plugin is installed, you can run it as follows:
```bash
kedro to_json
```

## Working with `click`

Commands must be provided as [`click` `Groups`](https://click.palletsprojects.com/en/7.x/api/#click.Group)

The `click Group` will be merged into the main CLI Group. In the process, the options on the group are lost, as is any processing that was done as part of its callback function.


## Project context

When they run, plugins may request information about the current project by creating a session and loading its context:

```python
from pathlib import Path

from kedro.framework.startup import _get_project_metadata
from kedro.framework.session import KedroSession


project_path = Path.cwd()
metadata = _get_project_metadata(project_path)
session = KedroSession.create(metadata.package_name, project_path)
context = session.load_context()
```

## Initialisation

If the plugin initialisation needs to occur prior to Kedro starting, it can declare the `entry_point` key `kedro.init`. This entry point must refer to a function that currently has no arguments, but for future proofing you should declare it with `**kwargs`.

## `global` and `project` commands

Plugins may also add commands to the Kedro CLI, which supports two types of commands:

* _global_ - available both inside and outside a Kedro project. Global commands use the `entry_point` key `kedro.global_commands`.
* _project_ - available only when a Kedro project is detected in the current directory. Project commands use the `entry_point` key `kedro.project_commands`.

## Suggested command convention

We use the following command convention: `kedro <plugin-name> <command>`, with `kedro <plugin-name>` acting as a top-level command group. This is our suggested way of structuring your plugin bit it is not necessary for your plugin to work.

## Hooks

You can develop hook implementations and have them automatically registered to the project context when the plugin is installed. To enable this for your custom plugin, simply add the following entry in your `setup.py`:

```python
setup(entry_points={"kedro.hooks": ["plugin_name = plugin_name.plugin:hooks"]},)
```

where `plugin.py` is the module where you declare hook implementations:

```python
import logging

from kedro.framework.hooks import hook_impl


class MyHooks:
    @hook_impl
    def after_catalog_created(self, catalog):  # pylint: disable=unused-argument
        logging.info("Reached after_catalog_created hook")


hooks = MyHooks()
```

> *Note:* Here, `hooks` should be an instance of the class defining the hooks.


## CLI Hooks

You can also develop hook implementations to extend Kedro's CLI behaviour in your plugin. To find available CLI hooks, please visit [kedro.framework.cli.hooks](/kedro.framework.cli.hooks). To register CLI hooks developed in your plugin with Kedro, add the following entry in your project's `setup.py`:

```python
setup(entry_points={"kedro.cli_hooks": ["plugin_name = plugin_name.plugin:cli_hooks"]},)
```

where `plugin.py` is the module where you declare hook implementations:

```python
import logging

from kedro.framework.cli.hooks import cli_hook_impl


class MyCLIHooks:
    @cli_hook_impl
    def before_command_run(self, project_metadata, command_args):
        logging.info(
            "Command %s will be run for project %s", command_args, project_metadata
        )


cli_hooks = MyCLIHooks()
```

## Contributing process

When you are ready to submit your code:

1. Create a separate repository using our naming convention for `plugin`s (`kedro-<plugin-name>`)
2. Choose a command approach: `global` and / or `project` commands:
   - All `global` commands should be provided as a single `click` group
   - All `project` commands should be provided as another `click` group
   - The `click` groups are declared through the [`pkg_resources` entry_point system](https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins)
3. Include a `README.md` describing your plugin's functionality and all dependencies that should be included
4. Use GitHub tagging to tag your plugin as a `kedro-plugin` so that we can find it

## Supported Kedro plugins

- [Kedro-Docker](https://github.com/quantumblacklabs/kedro-docker), a tool for packaging and shipping Kedro projects within containers
- [Kedro-Airflow](https://github.com/quantumblacklabs/kedro-airflow), a tool for converting your Kedro project into an Airflow project
- [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz), a tool for visualising your Kedro pipelines

## Community-developed plugins

> *Note:* See the full list of plugins using the GitHub tag [kedro-plugin](https://github.com/topics/kedro-plugin).
> *Note:* Your plugin needs to have an [Apache 2.0 compatible license](https://www.apache.org/legal/resolved.html#category-a) to be considered for this list.

- [Kedro-Pandas-Profiling](https://github.com/BrickFrog/kedro-pandas-profiling), by [Justin Malloy](https://github.com/BrickFrog), uses [Pandas Profiling](https://github.com/pandas-profiling/pandas-profiling) to profile datasets in the Kedro catalog
- [find-kedro](https://github.com/WaylonWalker/find-kedro), by [Waylon Walker](https://github.com/WaylonWalker), automatically constructs pipelines using `pytest`-style pattern matching
- [kedro-static-viz](https://github.com/WaylonWalker/kedro-static-viz), by [Waylon Walker](https://github.com/WaylonWalker), generates a static [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz) site (HTML, CSS, JS)
- [steel-toes](https://github.com/WaylonWalker/steel-toes), by [Waylon Walker](https://github.com/WaylonWalker), prevents stepping on toes by automatically branching data paths
- [kedro-wings](https://github.com/tamsanh/kedro-wings), by [Tam-Sanh Nguyen](https://github.com/tamsanh), simplifies and speeds up pipeline creation by auto-generating catalog datasets
- [kedro-great](https://github.com/tamsanh/kedro-great), by [Tam-Sanh Nguyen](https://github.com/tamsanh), integrates Kedro with [Great Expectations](https://greatexpectations.io), enabling catalog-based expectation generation and data validation on pipeline run
- [Kedro-Accelerator](https://github.com/deepyaman/kedro-accelerator), by [Deepyaman Datta](https://github.com/deepyaman), speeds up pipelines by parallelizing I/O in the background
- [kedro-dataframe-dropin](https://github.com/mzjp2/kedro-dataframe-dropin), by [Zain Patel](https://github.com/mzjp2), lets you swap out pandas datasets for modin or RAPIDs equivalents for specialised use to speed up your workflows (e.g on GPUs)
- [kedro-kubeflow](https://github.com/getindata/kedro-kubeflow), by [Mateusz Pytel](https://github.com/em-pe) and [Mariusz Strzelecki](https://github.com/szczeles), lets you run and schedule pipelines on Kubernetes clusters using [Kubeflow Pipelines](https://www.kubeflow.org/docs/pipelines/overview/pipelines-overview/)
- [kedro-mlflow](https://github.com/Galileo-Galilei/kedro-mlflow), by [Yolan Honoré-Rougé](https://github.com/galileo-galilei), [Kajetan Maurycy Olszewski](https://github.com/kaemo), and [Takieddine Kadiri](https://github.com/takikadiri) facilitates [Mlflow](https://www.mlflow.org/) integration inside Kedro projects while enforcing [Kedro's principles](https://kedro.readthedocs.io/en/stable/12_faq/01_faq.html#what-are-the-primary-advantages-of-kedro). Its main features are modular configuration, automatic parameters tracking, datasets versioning, Kedro pipelines packaging and serving and automatic synchronization between training and inference pipelines for high reproducibility of machine learning experiments and ease of deployment. A tutorial is provided in the [kedro-mlflow-tutorial repo](https://github.com/Galileo-Galilei/kedro-mlflow-tutorial).
