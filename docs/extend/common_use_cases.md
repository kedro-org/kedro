# Common use cases

Kedro provides several built-in mechanisms that let you extend its behaviour. This document explains how to choose which mechanism to use for common scenarios.
Kedro provides several built-in mechanisms that let you extend its behaviour. This document explains how to choose which mechanism to use for common scenarios.

## Use Case 1: How to add extra behaviour to Kedro's execution timeline

The execution timeline of a Kedro pipeline is a sequence of actions performed by various Kedro library components. Examples include the [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/), [kedro.io.DataCatalog][], [kedro.pipeline.pipeline.Pipeline][], [kedro.pipeline.node.Node][], and [kedro.framework.context.KedroContext][].

At different points in the lifecycle of these components, you might want to add extra behaviour. For example, you could add extra computation for profiling purposes _before_ and _after_ a node runs. You might also insert behaviour around the I/O actions of a dataset, namely the `load` and `save` actions.

You can do this with [Hooks](./hooks/introduction.md) by defining the extra behaviour and when in the execution timeline it should be introduced.

## Use Case 2: How to integrate Kedro with additional data sources

You can use [`Datasets`](https://docs.kedro.org/projects/kedro-datasets/en/stable/) to interface with a range of data sources. If the data source you plan to use is not supported out of the box by Kedro, you can [create a custom dataset](./how_to_create_a_custom_dataset.md).

## Use Case 3: How to add or change CLI commands

If you want to customise a built-in Kedro command, such as `kedro run`, for a specific project, add a `cli.py` file that defines a custom `run()` function. Add the `cli.py` file at the same level as `settings.py`, which in a default project is the `src/PROJECT_NAME` directory. See the [template for the `cli.py` file](../getting-started/commands_reference.md#customise-or-override-project-specific-kedro-commands).


If you want to customise a Kedro command from a command group, such as `kedro pipeline` or `kedro jupyter`, you need to import the corresponding click command group from the Kedro framework `cli`. For `kedro pipeline` commands this would be `from kedro.framework.cli.pipeline import pipeline`, and for `kedro jupyter` commands `from kedro.framework.cli.jupyter import jupyter`. **Note**: you must still add the `cli` click group from the snippet above, even if you do not change it.

You can then add or overwrite any command by adding it to the click group, as in the snippet below:
```
@jupyter.command("notebook")
@env_option(
    help="Open a notebook"
)
def notebook_run(...):
    == ADD YOUR CUSTOM NOTEBOOK COMMAND CODE HERE ==
```

To inject additional CLI commands intended to be reused across projects, see [our plugin system](./plugins.md). An example of one such command is the `kedro viz run` command introduced by the [Kedro-Viz plugin](https://github.com/kedro-org/kedro-viz). This command is intended to work on every Kedro project which is why it comes from a standalone plugin.

!!! note
    Your plugin's implementation can take advantage of other extension mechanisms such as Hooks.

## Use Case 4: How to customise the initial boilerplate of your project

Sometimes you might want to tailor the starting boilerplate of a Kedro project to your specific needs. For example, your organisation might have a standard CI script that you want to include in every new Kedro project. To this end, see the [guide for creating Kedro starters](./create_a_starter.md).
