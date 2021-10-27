# Common use cases

Kedro has a few built-in mechanisms for you to extend its behaviour. This document explains how to select which mechanism to employ for the most common use cases.

## Use Case 1: How to add extra behaviour to Kedro's execution timeline

The execution timeline of a Kedro pipeline can be thought of as a sequence of actions performed by various Kedro library components, such as the [DataSets](/kedro.extras.datasets), [DataCatalog](/kedro.io.DataCatalog), [Pipeline](/kedro.pipeline.Pipeline), and [Node](/kedro.pipeline.node.Node).

At different points in the lifecycle of these components, you may want to add extra behaviour. For example, you could add extra computation for profiling purposes _before_ and _after_ a node runs or _before_ and _after_ the I/O actions of a dataset, namely the `load` and `save` actions.

Before Kedro 0.17.0, we added a few different APIs to allow you to extend Kedro's behaviour. For example, to allow extra behaviour _before_ and _after_ a node runs, we introduced the [decorators](07_decorators.md) API. Similarly, to allow extra behaviour _before_ and _after_ dataset I/O, we introduced the [transformers](06_transformers.md) API.

While we addressed some immediate use cases, we have since decided to provide just one, single way to extend Kedro's execution timeline: Hooks. So, from Kedro version 0.17.0, we now deprecate decorators and transformers in favour of [Hooks](./02_hooks.md), which will be the recommended approach when you need to extend Kedro's execution timeline.

## Use Case 2: How to integrate Kedro with additional data sources

You can use [DataSets](/kedro.extras.datasets) to interface with various different data sources. If the data source you plan to use is not supported out of the box by Kedro, you can [create a custom dataset](03_custom_datasets.md).

## Use Case 3: How to add or modify CLI commands

If you want to customise a built-in Kedro command, such as `kedro run`, for a specific project, add a `cli.py` file that defines a custom `run()` function. You should add the `cli.py` file at the same level as `settings.py`. A template for the `cli.py` file is in the section below.

<details>
<summary><b>Click to expand</b></summary>

```
"""Command line tools for manipulating a Kedro project.
Intended to be invoked via `kedro`."""
import click
from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    _config_file_callback,
    _reformat_load_versions,
    _split_params,
    env_option,
    split_string,
)

from kedro.framework.cli.project import (
    FROM_INPUTS_HELP, TO_OUTPUTS_HELP, FROM_NODES_HELP, TO_NODES_HELP, NODE_ARG_HELP,
    RUNNER_ARG_HELP, PARALLEL_ARG_HELP, ASYNC_ARG_HELP, TAG_ARG_HELP, LOAD_VERSION_HELP,
    PIPELINE_ARG_HELP, CONFIG_FILE_HELP, PARAMS_ARG_HELP
)


@click.group(context_settings=CONTEXT_SETTINGS, name=__file__)
def cli():
    """Command line tools for manipulating a Kedro project."""


@cli.command()
@click.option(
    "--from-inputs", type=str, default="", help=FROM_INPUTS_HELP, callback=split_string
)
@click.option(
    "--to-outputs", type=str, default="", help=TO_OUTPUTS_HELP, callback=split_string
)
@click.option(
    "--from-nodes", type=str, default="", help=FROM_NODES_HELP, callback=split_string
)
@click.option(
    "--to-nodes", type=str, default="", help=TO_NODES_HELP, callback=split_string
)
@click.option("--node", "-n", "node_names", type=str, multiple=True, help=NODE_ARG_HELP)
@click.option(
    "--runner", "-r", type=str, default=None, multiple=False, help=RUNNER_ARG_HELP
)
@click.option("--parallel", "-p", is_flag=True, multiple=False, help=PARALLEL_ARG_HELP)
@click.option("--async", "is_async", is_flag=True, multiple=False, help=ASYNC_ARG_HELP)
@env_option
@click.option("--tag", "-t", type=str, multiple=True, help=TAG_ARG_HELP)
@click.option(
    "--load-version",
    "-lv",
    type=str,
    multiple=True,
    help=LOAD_VERSION_HELP,
    callback=_reformat_load_versions,
)
@click.option("--pipeline", type=str, default=None, help=PIPELINE_ARG_HELP)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help=CONFIG_FILE_HELP,
    callback=_config_file_callback,
)
@click.option(
    "--params", type=str, default="", help=PARAMS_ARG_HELP, callback=_split_params
)
def run(
    tag,
    env,
    parallel,
    runner,
    is_async,
    node_names,
    to_nodes,
    from_nodes,
    from_inputs,
    to_outputs,
    load_version,
    pipeline,
    config,
    params,
):
    """Run the pipeline."""

    == ADD YOUR CUSTOM RUN COMMAND CODE HERE ==

```
</details>

If you want to customise a Kedro command from a command group, such as `kedro pipeline` or `kedro jupyter`, you need to import the corresponding click command group from the Kedro framework `cli`. For `kedro pipeline` commands this would be `from kedro.framework.cli.pipeline import pipeline`, and for `kedro jupyter` commands `from kedro.framework.cli.jupyter import jupyter`. Note that you must still add the `cli` click group from the snippet above, even if you don't modify it.

You can then add or overwrite any command by adding it to the click group, as in the snippet below:
```
@jupyter.command("notebook")
@env_option(
    help="Open a notebook"
)
def notebook_run(...):
    == ADD YOUR CUSTOM NOTEBOOK COMMAND CODE HERE ==
```

To inject additional CLI commands intended to be reused across projects, please refer to our [plugins](./04_plugins.md) system. An example of one such command is the `kedro viz` command introduced by the official [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz) plugin. This command is intended to work on every Kedro project and therefore must be a standalone plugin.

```eval_rst
.. note::  Your plugin's implementation can take advantage of other extension mechanisms such as Hooks.
```

## Use Case 4: How to customise the initial boilerplate of your project

Sometimes you might want to tailor the starting boilerplate of a Kedro project to your specific needs. For example, your organisation might have a standard CI script that you want to include in every new Kedro project. To this end, please visit our guide to [create Kedro starters](./05_create_kedro_starters.md) to solve this extension requirement.
