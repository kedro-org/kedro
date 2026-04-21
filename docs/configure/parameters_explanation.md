# Parameters

## What are parameters?

Project parameters in Kedro are defined inside the `conf` folder in a file that has a filename starting with `parameters`, or are located inside a folder with name starting with `parameters`.
By default, in a new Kedro project, parameters are defined in the `parameters.yml` file, which is located in the project's `conf/base` directory. This file contains a dictionary of key-value pairs, where each key is a parameter name and each value is the corresponding parameter value.
These parameters can serve as input to nodes and are used when running the pipeline. By using parameters, you can make your Kedro pipelines more flexible and easier to configure, since you can change the behaviour of your nodes by modifying the `parameters.yml` file.

## How parameters work

If you have a group of parameters that determine the hyperparameters of your model, define them in a single location such as `conf/base/parameters.yml`. Keeping everything together reduces the chances of missing an update elsewhere in the codebase.

Parameters are added to the Data Catalog by Kedro as `MemoryDataset`s, which makes them accessible to your pipeline nodes just like any other dataset.

To learn how to use parameters in practice, see the [how-to guide on working with parameters](how_to_use_parameters.md).
