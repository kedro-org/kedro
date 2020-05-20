# Decorators

Welcome to `kedro.extras.decorators`, the home of Kedro's node and pipeline decorators, which enable additional functionality by wrapping your functions, for example:
 - Retry nodes that have failed to run
 - Profile how much memory is being consumed by a node

Further information on [node and pipeline decorators](https://kedro.readthedocs.io/en/stable/03_tutorial/04_create_pipelines.html#using-decorators-for-nodes-and-pipelines) has been added to the documentation. Before writing a decorator to implement a certain functionality that interacts a pipeline or node lifecycle event, you may want to consider using [Hooks](https://kedro.readthedocs.io/en/latest/04_user_guide/15_hooks.html) instead.

## What decorators are currently supported?
View a full list of supported decorators [**here**](https://kedro.readthedocs.io/en/stable/kedro.extras.decorators.html).

Examples of decorators supported include:
 - **A retry decorator**: A function decorator which catches exceptions from the wrapped function at most `n_times`, after which it bundles and propagates them. By default, all exceptions are caught, but you can narrow your scope using the `exceptions` argument. You can also specify the time delay (in seconds) between a failure and the next retry, using the `delay_sec` parameter.
 - **A node and pipeline memory profiler**: A function decorator which profiles the memory used when executing the function. The logged memory is collected by taking memory snapshots every 100ms, and includes memory used by children processes. The implementation uses the `memory_profiler` Python package under the hood.
 - **An argument validation decorator**: A function decorator which validates the especified arguments of the function from their type annotations. It is built from `pydantic` so it also supports validation of custom `pydantic` data models. For more information please refer to [`pydantic`'s docs](https://pydantic-docs.helpmanual.io/).

> _Note_: The node and pipeline memory profiler will only work on functions that take longer than 0.5s to execute, see [class documentation](memory_profiler.py) for more details.
> _Note_: The argument validation decorator only supports the validation of arguments with type annotations of the types supported by pydantic, see [supported types](https://pydantic-docs.helpmanual.io/usage/types/) for more details.

### What pre-requisites are required for the node and pipeline memory profiler?

On Unix-like operating systems, you will need to install a C-compiler and related build tools for your platform.

 #### macOS
 To install Command Line Tools for Xcode, run the following from the terminal:

 ```bash
 xcode-select --install
 ```

 #### GNU / Linux

 ##### Debian/Ubuntu

 The following command (run with root permissions) will install the `build-essential` metapackage for Debian-based distributions:

 ```bash
 apt-get update && apt-get install build-essential
 ```

 ##### Red Hat Enterprise Linux / Centos
 The following command (run with root permissions) will install the "Develop Tools" group of packages on RHEL / Centos:

 ```bash
 yum groupinstall 'Development Tools'
 ```
