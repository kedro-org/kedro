# Lifecycle management with `KedroSession`

> *Note:* This documentation is based on `Kedro 0.17.0`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

### Overview
A `KedroSession` allows you to:

* Manage the lifecycle of a Kedro run
* Persist runtime parameters with corresponding session IDs
* Traceback runtime parameters, such as CLI command flags and environment variables

`KedroSession` decouples Kedro's library components, managed by `KedroContext`, and any session data (both static and dynamic data). As a result, Kedro components and plugins can access session data without the need to import the `KedroContext` object and library components.

The main methods and properties of `KedroSession` are:

- `create()`: Create a new instance of ``KedroSession`` with  session data
- `load_context()`: Instantiate `KedroContext` object
- `close()`: Close the current session - we recommend that you [use the session object as a context manager](#create-a-session), which will call `close()` automatically, as opposed to calling the method explicitly
- `run()`: Run the pipeline with the arguments provided. See the [Running pipelines](../06_nodes_and_pipelines/04_run_a_pipeline) page for details

### Create a session

`KedroSession` can be used as a context manager to construct a new `KedroSession` with session data provided. You should prefer to use the context manager because it automatically closes the session after the exit. The following code example creates `KedroSession` object as a context manager and runs a pipeline inside the context.

```python
from kedro.framework.session import KedroSession

with KedroSession.create("<your-kedro-project-package-name>") as session:
    session.run()
```

You need to tell the `KedroSession` what is the package name of your Kedro
 project, so it can load your settings, nodes and pipelines.
Additionally, you can provide the following optional arguments in `KedroSession
.create()`:

- `project_path`: Path to the project root directory
- `save_on_close`: A boolean value to indicate whether or not to save the session to disk when it's closed
- `env`: Environment for the KedroContext
- `extra_params`: Optional dictionary containing extra project parameters
for the underlying `KedroContext`. If you specify it, it will update (and therefore take
precedence over) the parameters retrieved from the project configuration

When you want to access to the most recent session object, use a helper function `get_current_session()` as follows:

```python
from kedro.framework.session import get_current_session
session = get_current_session()
context = session.load_context()
context.catalog.load("my_data").head()
```
