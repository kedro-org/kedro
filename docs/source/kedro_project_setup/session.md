# Lifecycle management with `KedroSession`

## Overview
A `KedroSession` allows you to:

* Manage the lifecycle of a Kedro run
* Persist runtime parameters with corresponding session IDs
* Traceback runtime parameters, such as CLI command flags and environment variables

`KedroSession` decouples Kedro's library components, managed by `KedroContext`, and any session data (both static and dynamic data). As a result, Kedro components and plugins can access session data without the need to import the `KedroContext` object and library components.

The main methods and properties of `KedroSession` are:

- `create()`: Create a new instance of ``KedroSession`` with  session data
- `load_context()`: Instantiate `KedroContext` object
- `close()`: Close the current session — although we recommend that you [use the session object as a context manager](#create-a-session), which will call `close()` automatically, as opposed to calling the method explicitly
- `run()`: Run the pipeline with the arguments provided; see  [Running pipelines](../nodes_and_pipelines/run_a_pipeline) for details

## Create a session

The following code creates a `KedroSession` object as a context manager and runs a pipeline inside the context, with session data provided. The session automatically closes after exit:

```python
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from pathlib import Path

metadata = bootstrap_project(Path.cwd())
with KedroSession.create(metadata.package_name) as session:
    session.run()
```

You must tell `KedroSession` the package name of your Kedro project so it can load your settings, nodes and pipelines. Additionally, you can provide the following optional arguments in `KedroSession.create()`:

- `project_path`: Path to the project root directory
- `save_on_close`: A boolean value to indicate whether or not to save the session to disk when it's closed
- `env`: Environment for the `KedroContext`
- `extra_params`: Optional dictionary containing extra project parameters
for the underlying `KedroContext`; if specified, this will update (and therefore take precedence over) parameters retrieved from the project configuration
