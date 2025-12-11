# Frequently asked questions

This is a growing set of technical FAQs. The [product FAQs on the Kedro website](https://kedro.org/#faq) explain how Kedro can answer the typical use cases and requirements of data scientists, data engineers, machine learning engineers and product owners.


## Installing Kedro
* [How to install a development version of Kedro](https://github.com/kedro-org/kedro/wiki/Guidelines-for-contributing-developers)?

* **How to check the version of Kedro installed?**
  To check the version installed, type `kedro -V` in your terminal window.
* **Do you need Git installed to use Kedro?**
  Yes, users are expected to have Git installed when working with Kedro. This is a prerequisite for the `kedro new` flow. If Git is not installed, use the following workaround: `uvx kedro new -s https://github.com/kedro-org/kedro-starters/archive/1.0.0.zip --directory=spaceflights-pandas`

## Kedro documentation
* [Where to find the documentation about Kedro-Viz](https://docs.kedro.org/projects/kedro-viz/en/stable/)
* [Where to find the documentation for Kedro's datasets](https://docs.kedro.org/projects/kedro-datasets/en/stable/)

## Working with Notebooks

* [How to debug a Kedro project in a Jupyter notebook](../integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks.md#debugging-a-kedro-project-within-a-notebook)?
* [How to connect a Kedro project kernel to other Jupyter clients like JupyterLab](../integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks.md#ipython-jupyterlab-and-other-jupyter-clients)?
* [How to use the Kedro IPython extension in a notebook where launching a new kernel is not an option](../integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks.md#loading-the-project-with-the-kedroipython-extension)?
* [How to fix Line magic function `%reload_kedro` not found?](../integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks.md#loading-the-project-with-kedro-jupyter-notebook)

## Kedro project development

* [How to write your own Kedro starter projects](../extend/create_a_starter.md)?

## Configuration

* [How to change the setting for a configuration source folder](../configure/configuration_basics.md#how-to-change-the-setting-for-a-configuration-source-folder)?
* [How to change the configuration source folder at runtime](../configure/configuration_basics.md#how-to-change-the-configuration-source-folder-at-runtime)?
* [How to specify parameters at runtime](../configure/parameters.md#how-to-specify-parameters-at-runtime)?
* [How to read configuration from a compressed file](../configure/configuration_basics.md#how-to-read-configuration-from-a-compressed-file)?
* [How to access configuration in code](../configure/configuration_basics.md#how-to-access-configuration-in-code)?
* [How to load credentials in code](../configure/credentials.md#how-to-load-credentials-in-code)?
* [How to load parameters in code](../configure/parameters.md#how-to-load-parameters-in-code)?
* [How to specify additional configuration environments](../configure/configuration_basics.md#how-to-specify-additional-configuration-environments)?
* [How to change the default overriding configuration environment](../configure/configuration_basics.md#how-to-change-the-default-overriding-environment)?
* [How to use a single configuration environment](../configure/configuration_basics.md#how-to-use-a-single-configuration-environment)?
* [How to use Kedro logging without the Rich library](../develop/logging.md#how-to-use-logging-without-the-rich-library)

### Advanced topics

* [How to change which configuration files are loaded](../configure/advanced_configuration.md#how-to-change-which-configuration-files-are-loaded)?
* [How to use a custom configuration loader](../configure/advanced_configuration.md#how-to-use-a-custom-configuration-loader)?
* [How to ensure non default configuration files get loaded](../configure/advanced_configuration.md#how-to-ensure-non-default-configuration-files-get-loaded)?
* [How to bypass the configuration loading rules](../configure/advanced_configuration.md#how-to-bypass-the-configuration-loading-rules)?
* [How to do templating with the `OmegaConfigLoader`](../configure/advanced_configuration.md#how-to-do-templating-with-the-omegaconfigloader)?
* [How to use global variables with the `OmegaConfigLoader`](../configure/advanced_configuration.md#how-to-use-global-variables-with-the-omegaconfigloader)?
* [How to use resolvers in the `OmegaConfigLoader`](../configure/advanced_configuration.md#how-to-use-resolvers-in-the-omegaconfigloader)?
* [How to load credentials through environment variables](../configure/advanced_configuration.md#how-to-load-credentials-through-environment-variables)?
* [How to use Kedro with different project structure?](../tutorials/settings.md#use-kedro-without-the-src-folder)

## Data Catalog
* [How to create dataset entries in catalog.yml?](../catalog-data/data_catalog.md)
* [How to use the same file with different formats using transcoding?](../catalog-data/data_catalog_yaml_examples.md#read-the-same-file-using-different-datasets-with-transcoding)
* [How to use dataset factories?](../catalog-data/kedro_dataset_factories.md)
* [How to override the default dataset creation with a default dataset factory pattern?](../catalog-data/kedro_dataset_factories.md#how-to-override-the-default-dataset-creation-with-dataset-factories)
* [How to load and save incremental or partitioned datasets?](../catalog-data/partitioned_and_incremental_datasets.md)

## Advanced topics
* [How to use the `DataCatalog` programmatically in code?](../catalog-data/advanced_data_catalog_usage.md)

## Nodes and pipelines

* [How to create a new blank pipeline](../build/modular_pipelines.md#how-to-create-a-new-blank-pipeline-using-the-kedro-pipeline-create-command)?
* [How to reuse pipelines](../build/namespaces.md)?
* [How to use generator functions in a node](../build/nodes.md#how-to-use-generator-functions-in-a-node)?

## What is data engineering convention?

[Bruce Philp](https://github.com/bruceaphilp) and [Guilherme Braccialli](https://github.com/gbraccialli-qb) are the
brains behind a layered data-engineering convention as a model of managing data. You can find an [in-depth walk through of their convention](https://towardsdatascience.com/the-importance-of-layered-thinking-in-data-engineering-a09f685edc71) as a blog post on Medium.

Refer to the following table below for a high level guide to each layer's purpose

!!! note
    The data layers don’t have to exist locally in the `data` folder within your project, but we recommend that you structure your S3 buckets or other data stores in a similar way.

![data_engineering_convention](../meta/images/data_layers.png)

| Folder in data | Description                                                                                                                                                                                                                                                                                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Raw            | Initial start of the pipeline, containing the sourced data model(s) that should never be changed, it forms your single source of truth to work from. These data models are typically un-typed in most cases, for example, CSV files, but this will vary from case to case                                                                                                        |
| Intermediate   | Optional data model(s), which are introduced to type your `raw` data model(s), for example, converting string based values into their current typed representation                                                                                                                                                                                                  |
| Primary        | Domain specific data model(s) containing cleansed, transformed and wrangled data from either `raw` or `intermediate`, which forms your layer that you input into your feature engineering                                                                                                                                                                         |
| Feature        | Analytics specific data model(s) containing a set of features defined against the `primary` data, which are grouped by feature area of analysis and stored against a common dimension                                                                                                                                                                             |
| Model input    | Analytics specific data model(s) containing all `feature` data against a common dimension and for live projects against an analytics run date to ensure that you track the historical changes of the features over time                                                                                                                          |
| Models         | Stored, serialised pre-trained machine learning models                                                                                                                                                                                                                                                                                                            |
| Model output   | Analytics specific data model(s) containing the results generated by the model based on the `model input` data                                                                                                                                                                                                                                                    |
| Reporting      | Reporting data model(s) that are used to combine a set of `primary`, `feature`, `model input` and `model output` data used to drive the dashboard and the views constructed. It encapsulates and removes the need to define any blending or joining of data, improve performance and replacement of presentation layer without having to redefine the data models |
