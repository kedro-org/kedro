# Parameters and Credentials

This page explains what parameters and credentials are in Kedro, and how they work conceptually.

## Parameters

### What are parameters?

Project parameters in Kedro are defined inside the `conf` folder in a file that has a filename starting with `parameters`, or are located inside a folder with name starting with `parameters`.
By default, in a new Kedro project, parameters are defined in the `parameters.yml` file, which is located in the project's `conf/base` directory. This file contains a dictionary of key-value pairs, where each key is a parameter name and each value is the corresponding parameter value.
These parameters can serve as input to nodes and are used when running the pipeline. By using parameters, you can make your Kedro pipelines more flexible and easier to configure, since you can change the behaviour of your nodes by modifying the `parameters.yml` file.

### How parameters work

If you have a group of parameters that determine the hyperparameters of your model, define them in a single location such as `conf/base/parameters.yml`. Keeping everything together reduces the chances of missing an update elsewhere in the codebase.

Parameters are added to the Data Catalog by Kedro as `MemoryDataset`s, which makes them accessible to your pipeline nodes just like any other dataset.

To learn how to use parameters in practice, see the [how-to guide on working with parameters](how_to_use_parameters.md).

## Credentials

### What are credentials?

For security reasons, we strongly recommend that you *do not* commit any credentials or other secrets to version control.
Kedro is set up so that, by default, if a file inside the `conf` folder (and its subdirectories) contains `credentials` in its name, it is ignored by git.

Credentials configuration can be used on its own directly in code or [fed into the `DataCatalog`](../catalog-data/data_catalog.md).
If you prefer to store credentials in environment variables rather than a file, use the `OmegaConfigLoader` [to load credentials from environment variables](how_to_advanced_configuration.md#how-to-load-credentials-through-environment-variables) as described in the advanced configuration how-to guide.

To learn how to work with credentials in practice, see the [how-to guide on managing credentials](how_to_manage_credentials.md).
