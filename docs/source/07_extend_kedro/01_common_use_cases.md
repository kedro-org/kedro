# Common use cases

Kedro has a few built-in mechanisms for you to extend its behaviour. This document explains how to select which mechanism to employ for the most common use cases.

## Use Case 1: How to add extra behaviour to Kedro's execution timeline

The execution timeline of a Kedro pipeline can be thought of as a sequence of actions performed by various Kedro library components, such as the [DataSets](/kedro.extras.datasets), [DataCatalog](/kedro.io.DataCatalog), [Pipeline](/kedro.pipeline.Pipeline), and [Node](/kedro.pipeline.node.Node).

At different points in the lifecycle of these components, you may want to add extra behaviour. For example, you could add extra computation for profiling purposes _before_ and _after_ a node runs or _before_ and _after_ the I/O actions of a dataset, namely the `load` and `save` actions.

Before Kedro 0.17.0, we added a few different APIs to allow you to extend Kedro's behaviour. For example, to allow extra behaviour _before_ and _after_ a node runs, we introduced the [decorators](07_decorators.md) API. Similarly, to allow extra behaviour _before_ and _after_ dataset I/O, we introduced the [transformers](06_transformers.md) API.

While we addressed some immediate use cases, we have since decided to provide just one, single way to extend Kedro's execution timeline: Hooks. So, from Kedro version 0.17.0, we now deprecate decorators and transformers in favour of [Hooks](./02_hooks.md), which will be the recommended approach when you need to extend Kedro's execution timeline.

## Use Case 2: How to integrate Kedro with additional data sources

You can use [DataSets](/kedro.extras.datasets) to interface with various different data sources. If the data source you plan to use is not supported out of the box by Kedro, you can [create a custom dataset](03_custom_datasets.md).

## Use Case 3: How to add CLI commands that are reusable across projects

To inject additional CLI commands intended to be reused across projects, please refer to our [plugins](./04_plugins.md) system. An example of one such command is the `kedro viz` command introduced by the official [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz) plugin. This command is intended to work on every Kedro project and therefore must be a standalone plugin. On the other hand, if you just want to customise built-in Kedro commands, such as `kedro run` for a specific project, please modify the `cli.py` file in your project instead.

> *Note:* Please note that your plugin's implementation can take advantage of other extension mechanisms such as Hooks.

## Use Case 4: How to customise the initial boilerplate of your project

Sometimes you might want to tailor the starting boilerplate of a Kedro project to your specific needs. For example, your organisation might have a standard CI script that you want to include in every new Kedro project. To this end, please visit our guide to [create Kedro starters](./05_create_kedro_starters.md) to solve this extension requirement.
