# How to use Kedro from Marimo and non-Jupyter environments

This guide explains how to set up Kedro programmatically from non-Jupyter environments (Python scripts or Streamlit apps) and modern notebook interfaces like [Marimo](https://marimo.io/) without relying on IPython magics. Marimo notebooks are reactive notebook with a focus on reproducibility, they are executable as a script and shareable as an app. Reactivity in this case ensures that code and outputs are always in sync.

## Overview

Kedro Jupyter notebook users rely on the magic command `%load_ext kedro.ipython` to source their catalog, context, pipelines and session objects, see [Kedro and Notebooks](../integrations-and-plugins/kedro_and_notebooks.md) for more. This magic command automatically finds the location of the root Kedro project.

Such magic commands are not available in modern notebook interfaces such as Marimo or in short Python scripts. Yet, using Kedro for sharing configuration, credentials, or the data catalog across a project is still desired when developing data science projects.

## Dynamically loading Kedro config

Instead of relying on magic, use the following script to automatically find the Kedro root and load the Kedro session objects:

```python
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.framework.project import configure_project
from kedro.utils import find_kedro_project

# Get project root
current_dir = Path(__file__).resolve().parent
project_root = find_kedro_project(current_dir)
bootstrap_project(Path(project_root))

# Create and use the session
with KedroSession.create(project_path=project_root) as session:
    context = session.load_context()
    catalog = context.catalog
    credentials = context.config_loader["credentials"]
    data = catalog.load("mytable")
```

This enables loading Kedro settings, including catalog and credentials, without using IPython magic.
