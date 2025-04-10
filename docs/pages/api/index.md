Kedro is a framework that makes it easy to build robust and scalable data pipelines by providing uniform project templates, data abstraction, configuration and pipeline assembly.

## Modules

| Name                                   | Description                                      |
|----------------------------------------|--------------------------------------------------|
| [`kedro.config`](config/kedro.config.md) | Provides functionality for loading Kedro configuration from different file formats.  |
| [`kedro.framework`](framework/kedro.framework.md) | provides Kedro's framework components  |
| [`kedro.io`](io/kedro.io.md)        | provides functionality to read and write to a number of datasets.    |
| [`kedro.ipython`](ipython/kedro.ipython.md) | This script creates an IPython extension to load Kedro-related variables in local scope.    |
| [`kedro.logging`](kedro.logging.md) |                                                  |
| [`kedro.pipeline`](pipeline/kedro.pipeline.md) | provides functionality to define and execute data-driven pipelines.      |
| [`kedro.runner`](runner/kedro.runner.md) | provides runners that are able to execute Pipeline instances. |
| [`kedro.utils`](kedro.utils.md) | This module provides a set of helper functions being used across different components of kedro package.          |

## Functions
| Name                                   | Description                                      |
|----------------------------------------|--------------------------------------------------|
| [`load_ipython_extension`](kedro.load_ipython_extension.md) |   |


## Exceptions
| Name                                   | Description                                      |
|----------------------------------------|--------------------------------------------------|
| [`KedroDeprecationWarning`](kedro.KedroDeprecationWarning.md) | Custom class for warnings about deprecated Kedro features.  |
| [`KedroPythonVersionWarning`](kedro.KedroPythonVersionWarning.md) | Custom class for warnings about incompatibilities with Python versions.  |
