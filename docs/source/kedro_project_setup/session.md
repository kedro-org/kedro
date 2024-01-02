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

bootstrap_project(Path.cwd())
with KedroSession.create() as session:
    session.run()
```

You can provide the following optional arguments in `KedroSession.create()`:

- `project_path`: Path to the project root directory
- `save_on_close`: A boolean value to indicate whether or not to save the session to disk when it's closed
- `env`: Environment for the `KedroContext`
- `extra_params`: Optional dictionary containing extra project parameters
for the underlying **`KedroContext`**; if specified, this will update (and therefore take precedence over) parameters retrieved from the project configuration

## `bootstrap_project` and `configure_project`
```{image} ../meta/images/kedro-session-creation.png
:alt: mermaid-General overview diagram for KedroSession creation
```

% Mermaid code, see https://github.com/kedro-org/kedro/wiki/Render-Mermaid-diagrams
% graph LR
%  subgraph Kedro Startup Flowchart
%    A[bootstrap_project] -->|Read pyproject.toml| B
%    A -->|Add project root to sys.path| B[configure_project]
%    C[Initialize KedroSession]
%    B --> |Read settings.py| C
%    B --> |Read pipeline_registry.py| C
%  end


Both `bootstrap_project` and `configure_project` handle the setup of a Kedro project, but there are subtle differences. `bootstrap_project` is used for project mode, and `configure_project` is used for packaged mode.

In most cases, you don't need to use these functions because Kedro's CLI already runs them at startup, i.e. `kedro run`. If you want to [interact with Kedro Project programtically in an interactive session such as Notebook](../notebooks_and_ipython/kedro_and_notebooks.md#reload_kedro-line-magic), you can use the `%reload_kedro` with Jupyter or IPython. You should only use these functions directly if none of these methods work.



### `bootstrap_project`

This function uses `configure_project` under the hood. Additionally, it reads metadata from `pyproject.toml` and adds the project root to `sys.path`. This ensures your project can be imported as a Python package. This is usually used when you are working with the source code of a Kedro Project.

### `configure_project`

This function reads `settings.py` and `pipeline_registry.py` and registers the configuration before Kedro's run starts. If you have an packaged Kedro project, you only need to run `configure_project` before executing your pipeline.
