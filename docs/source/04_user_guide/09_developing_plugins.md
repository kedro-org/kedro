# Developing Kedro plugins

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

## Overview

Kedro uses various entry points in the [`pkg_resources` entry_point system](https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins) to provide plugin functionality.

While running, plugins may request information about the current project by calling `kedro.cli.get_project_context(key, default=NO_DEFAULT)`.

This function provides access to the verbose flag via the key `verbose` and to anything returned by the project's `__kedro_context__`. The returned context dictionary must contain at least the following keys and values:
* _template_version_: the version of Kedro the project was created with, or `None` if the project was not created with `kedro new`.
* _project_path_: the path to the directory where `kedro_cli.py` is located.
* _get_config_: a function that takes the `project_path` and returns a `kedro.config.ConfigLoader` instance.
* _create_catalog_: a function that takes the config returned by `get_config` and returns a kedro.io.DataCatalog instance.
* _create_pipeline_: a function that returns a kedro.pipeline.Pipeline instance.

>*Note*: Plugins may require additional keys be added to `__kedro_context__` in `run.py`.

## Initialisation

If the plugin needs to do initialisation prior to Kedro starting, it can declare the `entry_point` key `kedro.init`. This entry point must refer to a function that currently has no arguments, but for future proofing you should declare it with `**kwargs`.

## global and project commands

Plugins may also add commands to the Kedro CLI, which supports two types of commands:
* _global_ - available both inside and outside a Kedro project
* _project_ - available only when a Kedro project is detected in the current directory.

Global commands use the `entry_point` key `kedro.global_commands`. Project commands use the `entry_point` key `kedro.project_commands`.

## Working with `click`

Commands must be provided as [`click` `Groups`](https://click.palletsprojects.com/en/7.x/api/#click.Group)

The `click` `Group` will be merged into the main CLI Group. In the process, the options on the group are lost, as is any processing that was done as part of its callback function.

## Example of a simple plugin

A simple plugin that prints the pipeline as JSON might look like:

`kedrojson/plugin.py`

```python
import click
from kedro.cli import get_project_context


@click.group(name="JSON")
def commands():
    """ Kedro plugin for printing the pipeline in JSON format """
    pass


@commands.command()
def to_json():
    """ Display the pipeline in JSON format """
    pipeline = get_project_context('create_pipeline')()
    print(pipeline.to_json())
```

And have the following entry_points config in `setup.py`:
```python
entry_points={
    'kedro.project_commands': ['kedrojson = kedrojson.plugin:commands'],
}
```

Once the plugin is installed, you can run it as follows:
```bash
kedro to_json
```
