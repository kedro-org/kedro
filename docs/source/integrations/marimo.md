# How to use Kedro from Marimo and non-Jupyter environments

This guide explains how to set up Kedro programmatically without relying on IPython magics, making it compatible with non-Jupyter environments (python scripts or streamlit apps) and modern notebook interfaces like Marimo.

## Overview

Kedro Jupyter notebook users rely on the magic command `%load_ext kedro.ipython` to source their catalog, context, pipelines and session objects, see [Kedro and Notebooks](../notebooks_and_ipython/kedro_and_notebooks.md) for more. This magic command automatically finds the location of the root kedro project, avoiding having users hardcode paths to their configuration files.

Such magic commands are not available in modern notebook interfaces such as marimo or in simple python scripts. Yet, using Kedro for sharing configuration, credentials or the data catalog across a project is still desired when developing data science projects.

## Dynamically loading kedro config

Instead of relying on magic, use the following script to automatically find the kedro root and load the kedro session objects:

```python
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.framework.project import configure_project
from kedro.utils import _find_kedro_project

# Get project root
current_dir = Path(__file__).resolve().parent
project_root = _find_kedro_project(current_dir)
bootstrap_project(Path(project_root))

# Create and use the session
with KedroSession.create(project_path=project_root) as session:
    context = session.load_context()
    catalog = context.catalog
    credentials = context.config_loader["credentials"]
    data = catalog.load("mytable")
```

This enables loading Kedro settings, including catalog and credentials, without using IPython magic.
