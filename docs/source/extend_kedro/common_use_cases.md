# Common use cases

Kedro has a few built-in mechanisms for you to extend its behaviour. This document explains how to select which mechanism to employ for the most common use cases.

## Use Case 1: How to add extra behaviour to Kedro's execution timeline

The execution timeline of a Kedro pipeline can be thought of as a sequence of actions performed by various Kedro library components, such as the [DataSets](/kedro.extras.datasets), [DataCatalog](/kedro.io.DataCatalog), [Pipeline](/kedro.pipeline.Pipeline), [Node](/kedro.pipeline.node.Node) and [KedroContext](/kedro.framework.context.KedroContext).

At different points in the lifecycle of these components, you might want to add extra behaviour: for example, you could add extra computation for profiling purposes _before_ and _after_ a node runs, or _before_ and _after_ the I/O actions of a dataset, namely the `load` and `save` actions.

This can now achieved by using [Hooks](../hooks/introduction.md), to define the extra behaviour and when in the execution timeline it should be introduced.

## Use Case 2: How to integrate Kedro with additional data sources

You can use [DataSets](/kedro.extras.datasets) to interface with various different data sources. If the data source you plan to use is not supported out of the box by Kedro, you can [create a custom dataset](custom_datasets.md).

## Use Case 3: How to add or modify CLI commands

If you want to customise a built-in Kedro command, such as `kedro run`, for a specific project, add a `cli.py` file that defines a custom `run()` function. You should add the `cli.py` file at the same level as `settings.py`, which is usually the `src/PROJECT_NAME` directory. See the [template for the `cli.py` file](../development/commands_reference.md#customise-or-override-project-specific-kedro-commands).


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

To inject additional CLI commands intended to be reused across projects, please refer to [our plugin system](./plugins.md). An example of one such command is the `kedro viz` command introduced by the [Kedro-Viz plugin](https://github.com/kedro-org/kedro-viz). This command is intended to work on every Kedro project and therefore must be a standalone plugin.

```{note}
Your plugin's implementation can take advantage of other extension mechanisms such as Hooks.
```

## Use Case 4: How to customise the initial boilerplate of your project

Sometimes you might want to tailor the starting boilerplate of a Kedro project to your specific needs. For example, your organisation might have a standard CI script that you want to include in every new Kedro project. To this end, please visit our [guide to create Kedro starters](./create_kedro_starters.md) to solve this extension requirement.
