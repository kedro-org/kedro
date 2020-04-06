# Developing Kedro plugins

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

The functionality of Kedro can be extended using its `plugin` framework, which is designed to reduce the complexity involved in creating new features for Kedro while allowing you to inject additional commands into the CLI. Plugins are developed as separate Python packages that exist outside of any Kedro project.

## Overview

Kedro uses various entry points in the [`pkg_resources` entry_point system](https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins) to provide plugin functionality.

While running, plugins may request information about the current project by calling `kedro.cli.get_project_context()`.

This function provides access to the verbose flag via the key `verbose` and to anything returned by the project's `KedroContext`. The returned instance of `ProjectContext(KedroContext)` class must contain at least the following properties and methods:
* `project_version`: the version of Kedro the project was created with, or `None` if the project was not created with `kedro new`.
* `project_path`: the path to the directory where `.kedro.yml` is located.
* `config_loader`: an instance of `kedro.config.ConfigLoader`.
* `catalog`: an instance of `kedro.io.DataCatalog`.
* `pipeline`: an instance of `kedro.pipeline.Pipeline`.

>*Note*: Plugins may require additional keys to be added to `ProjectContext` in `run.py`.


>*Note*: `kedro.cli.get_project_context(key)`, where `key` is `get_config`, `create_catalog`, `create_pipeline`, `template_version`, `project_name` and `project_path`, is deprecated as of `Kedro 0.15.0`, and will be removed for future versions.
## Initialisation

If the plugin needs to do initialisation prior to Kedro starting, it can declare the `entry_point` key `kedro.init`. This entry point must refer to a function that currently has no arguments, but for future proofing you should declare it with `**kwargs`.

## global and project commands

Plugins may also add commands to the Kedro CLI, which supports two types of commands:
* _global_ - available both inside and outside a Kedro project
* _project_ - available only when a Kedro project is detected in the current directory.

Global commands use the `entry_point` key `kedro.global_commands`. Project commands use the `entry_point` key `kedro.project_commands`.

### Suggested command convention

We use the following command convention: `kedro <plugin-name> <command>`. With `kedro <plugin-name>` acting as a top-level command group. Note, this is a suggested way of structuring your plugin and is not necessary for your plugin to work.

## Working with `click`

Commands must be provided as [`click` `Groups`](https://click.palletsprojects.com/en/7.x/api/#click.Group)

The `click` `Group` will be merged into the main CLI Group. In the process, the options on the group are lost, as is any processing that was done as part of its callback function.

## Contributing process

When you are ready to submit your code:

 1. Create a separate repository using our naming convention for `plugin`s (`kedro-<plugin-name>`)
 2. Choose a command approach, plugins can have `global` and / or `project` commands
   - All `global` commands should be provided as a single `click` group
   - All `project` commands should be provided as another `click` group
   - The `click` groups are declared through the [`pkg_resources` entry_point system](https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins)
 3. Include a `README.md` describing your `plugin`'s functionality and all dependencies that should be included
 4. Use GitHub tagging to tag your plugin as a `kedro-plugin` so that we can find it

>*Note:* In future, we will feature a list of "Plugins by Contributors". Your plugin needs to have an [Apache 2.0 compatible license](https://www.apache.org/legal/resolved.html#category-a) to be considered for this list.

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
    context = get_project_context()
    print(context.pipeline.to_json())
```

And have the following entry_points config in `setup.py`:
```python
entry_points={
    "kedro.project_commands": ["kedrojson = kedrojson.plugin:commands"],
}
```

Once the plugin is installed, you can run it as follows:
```bash
kedro to_json
```

## Supported plugins

- [Kedro-Docker](https://github.com/quantumblacklabs/kedro-docker), a tool for packaging and shipping Kedro projects within containers
- [Kedro-Airflow](https://github.com/quantumblacklabs/kedro-airflow), a tool for converting your Kedro project into an Airflow project
- [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz), a tool for visualising your Kedro pipelines

## Community-developed plugins

- [Kedro-Pandas-Profiling](https://github.com/BrickFrog/kedro-pandas-profiling) by [Justin Malloy](https://github.com/BrickFrog), a simple plugin that uses [Pandas-Profiling](https://github.com/pandas-profiling/pandas-profiling) to profile datasets in the Kedro catalog
