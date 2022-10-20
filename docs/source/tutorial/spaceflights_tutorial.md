# Kedro spaceflights tutorial

In this tutorial, we illustrate the steps for a typical Kedro workflow with an example that constructs nodes and pipelines for the price-prediction model.

**Scenario**: *It is 2160 and the space tourism industry is booming. Globally, thousands of space shuttle companies take tourists to the Moon and back. You have been able to source amenities offered in each space shuttle, customer reviews and company information.*

**Project**: *You want to construct a model that predicts the price for each trip to the Moon and the corresponding return flight.*

In the text, we assume that you have created an empty Kedro project; we show the steps necessary to convert it into a working project. The tutorial guides you to copy and paste example code into the Kedro project. It takes approximately two hours to complete. 

```{note}
You may prefer to get up and running more swiftly so we provide the same example as a [Kedro starter](../get_started/starters.md) to generate a project with the working code in-place, so you can follow along without copy/pasting.
```

## Kedro project development workflow

When you build a Kedro project, you will typically follow a standard development workflow:

![](../meta/images/typical_workflow.png)

### 1. Set up the project template

* Create a new project with `kedro new`
* Install project dependencies with `pip install -r src/requirements.txt`
* Configure the following in the `conf` folder:
	* Logging
	* Credentials and any other sensitive / personal content

### 2. Set up the data

* Add data to the `data/` folder
* Reference all datasets for the project in the `conf/base/catalog.yml` file

### 3. Create the pipeline

* Create the data transformation steps as Python functions
* Add your functions as nodes, to construct the pipeline
* Choose how to run the pipeline: sequentially or in parallel

### 4. Package the project

 * Build the project documentation
 * Package the project for distribution


