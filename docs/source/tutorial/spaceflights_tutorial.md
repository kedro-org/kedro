# Kedro spaceflights tutorial

In this tutorial, we illustrate the steps for a typical Kedro workflow with an example that constructs nodes and pipelines for the price-prediction model.

In the text, we assume that you have created an empty Kedro project; we show the steps necessary to convert it into a working project. The tutorial guides you to copy and paste example code into the Kedro project. It takes approximately two hours to complete. 

```{note}
You may prefer to get up and running more swiftly. We also provide the example as a [Kedro starter](../get_started/starters.md) so you can follow along without copy/pasting. 
```

## Scenario

*It is 2160 and the space tourism industry is booming. Globally, thousands of space shuttle companies take tourists to the Moon and back. You have been able to source amenities offered in each space shuttle, customer reviews and company information.*

**Project**: *You want to construct a model that predicts the price for each trip to the Moon and the corresponding return flight.*

![](../meta/images/moon-rocket.gif)


## Terminology

The Kedro specific terminology we use in the tutorial will be explained as we introduce it (and we provide links to further information in the [glossary](../resources/glossary.md)). We use some additional terminology which may not be familiar to every reader, such as:

* "**project root directory**" or "**root directory**": This is the parent folder for the entire project, it is the top level folder that contains all other files and directories associated with the project.
* "**dependencies**": These are Python packages, or libraries, that an individual project depends upon in order to complete a task. For example, the Spaceflights tutorial project depends on the [scikit-learn](https://scikit-learn.org/stable/) library.
* "**standard development workflow**"




