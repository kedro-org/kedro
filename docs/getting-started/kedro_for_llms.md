---
description: "Compact reference for LLMs and coding agents: Kedro project layout, a minimal pipeline, core API and CLI indices, catalog rules, common errors, and how to fetch these docs as Markdown."
---

# Kedro for LLMs

This page is a single-file cheatsheet for LLMs and coding agents. It covers what an agent needs to write correct Kedro code in one pass and links to the full documentation for everything else. Follow the links for detail; this page does not repeat them.

<!-- vale Kedro.headings = NO -->

## Fetch documentation as Markdown

<!-- vale Kedro.headings = YES -->

Use [`llms.txt`](https://docs.kedro.org/en/stable/llms.txt) as the machine-readable index of these docs. It lists every documentation page with a one-line description.

To fetch any page as Markdown instead of HTML, send this request header:

```text
Accept: text/markdown, text/html;q=0.9
```

Keep the `text/html` fallback. Read the Docs converts pages to Markdown on request, and pages over 2 MB return HTTP 406 instead of Markdown when the fallback is missing.

## Project layout

`kedro new` creates this structure. Code lives in `src/<package_name>/`, and configuration lives in `conf/`.

```text
<project_root>/
├── conf/
│   ├── base/                 # shared configuration, committed to version control
│   │   ├── catalog.yml       # dataset definitions
│   │   └── parameters.yml    # parameters, read with the "params:" prefix
│   ├── local/                # machine-specific overrides and credentials.yml, not committed
│   └── logging.yml
├── data/                     # 01_raw … 08_reporting (data layers)
├── notebooks/
├── pyproject.toml            # marks the project root; contains [tool.kedro]
├── src/<package_name>/
│   ├── pipeline_registry.py  # register_pipelines()
│   ├── settings.py           # Hooks, config loader, catalog class
│   └── pipelines/
│       └── <pipeline_name>/
│           ├── nodes.py      # plain Python functions
│           └── pipeline.py   # create_pipeline() returns a Pipeline
└── tests/
```

`kedro pipeline create <pipeline_name>` adds a new folder under `pipelines/` and a `conf/base/parameters_<pipeline_name>.yml` file.

## Minimal pipeline

Nodes are plain Python functions. Kedro connects them through dataset names, not function calls.

```python
# src/<package_name>/pipelines/data_processing/nodes.py
import pandas as pd


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    companies["iata_approved"] = companies["iata_approved"] == "t"
    return companies


def filter_companies(companies: pd.DataFrame, min_rating: float) -> pd.DataFrame:
    return companies[companies["company_rating"] >= min_rating]
```

```python
# src/<package_name>/pipelines/data_processing/pipeline.py
from kedro.pipeline import Node, Pipeline

from .nodes import filter_companies, preprocess_companies


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocess_companies_node",
            ),
            Node(
                func=filter_companies,
                inputs=["preprocessed_companies", "params:min_rating"],
                outputs="filtered_companies",
                name="filter_companies_node",
            ),
        ]
    )
```

```yaml
# conf/base/catalog.yml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv

filtered_companies:
  type: pandas.ParquetDataset
  filepath: data/03_primary/filtered_companies.parquet
```

```yaml
# conf/base/parameters.yml
min_rating: 0.9
```

`preprocessed_companies` has no catalog entry, so Kedro keeps it in memory for the duration of the run. The default `pipeline_registry.py` calls `find_pipelines()`, which discovers every `create_pipeline()` under `pipelines/`. Run the result with `kedro run`.

Longer walk-through: [spaceflights tutorial](../tutorials/spaceflights_tutorial.md).

## Core API index

| Object                                                                                                                                                  | Import                                               | Use it to                                                                                              | Guide                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| \[`Node`\][kedro.pipeline.node.Node]                                                                                                                    | `from kedro.pipeline import Node`                    | Wrap a function with named `inputs` and `outputs`. The `node()` factory function does the same.        | [Nodes](../build/nodes.md)                                                                 |
| \[`Pipeline`\][kedro.pipeline.pipeline.Pipeline]                                                                                                        | `from kedro.pipeline import Pipeline`                | Combine nodes. Accepts `namespace`, `inputs`, `outputs`, `parameters`, and `tags` to reuse a pipeline. | [Pipeline object](../build/pipeline_introduction.md), [Namespaces](../build/namespaces.md) |
| \[`find_pipelines`\][kedro.framework.project.find_pipelines]                                                                                            | `from kedro.framework.project import find_pipelines` | Discover `create_pipeline()` functions in `pipelines/`.                                                | [Pipeline registry](../build/pipeline_registry.md)                                         |
| \[`DataCatalog`\][kedro.io.DataCatalog]                                                                                                                 | `from kedro.io import DataCatalog`                   | Load and save datasets by name. Built from `catalog.yml` in a project.                                 | [Data Catalog](../catalog-data/data_catalog.md)                                            |
| \[`AbstractDataset`\][kedro.io.AbstractDataset]                                                                                                         | `from kedro.io import AbstractDataset`               | Subclass to create a custom dataset with `load`, `save`, and `_describe`.                              | [Custom datasets](../extend/how_to_create_a_custom_dataset.md)                             |
| \[`KedroSession`\][kedro.framework.session.session.KedroSession]                                                                                        | `from kedro.framework.session import KedroSession`   | Run a project from Python.                                                                             | [Kedro sessions](../extend/session.md)                                                     |
| \[`SequentialRunner`\][kedro.runner.SequentialRunner], \[`ThreadRunner`\][kedro.runner.ThreadRunner], \[`ParallelRunner`\][kedro.runner.ParallelRunner] | `from kedro.runner import ...`                       | Choose how nodes execute. `SequentialRunner` is the default.                                           | [Run a pipeline](../build/run_a_pipeline.md)                                               |
| \[`llm_context_node`\][kedro.pipeline.llm_context.llm_context_node]                                                                                     | `from kedro.pipeline import llm_context_node`        | Bundle an LLM, prompts, and tools from the catalog into one node input.                                | [LLM context node](../build/llm_context_node.md)                                           |
| \[`get_project_snapshot`\][kedro.inspection.get_project_snapshot]                                                                                       | `from kedro.inspection import get_project_snapshot`  | Read a project's pipelines, nodes, and datasets without running it.                                    | [Inspect a project](../inspect/inspect-project.md)                                         |

## Data Catalog rules

- `type` names a dataset class. Short names such as `pandas.CSVDataset` resolve to the [`kedro-datasets`](https://docs.kedro.org/projects/kedro-datasets/en/stable/) package, which you install separately with the matching extra, for example `pip install "kedro-datasets[pandas-csvdataset]"`.
- A node input or output with no catalog entry and no matching pattern becomes an in-memory `MemoryDataset`. It does not persist after the run.
- Parameters are node inputs with the `params:` prefix, for example `"params:model_options.test_size"`. Use the input name `"parameters"` to pass every parameter as a dictionary.
- A dataset factory matches several dataset names with one entry, for example `"{name}_data"` with `filepath: data/01_raw/{name}_data.csv`. See [dataset factories](../catalog-data/kedro_dataset_factories.md).
- Credentials go in `conf/local/credentials.yml`. Reference them by key with `credentials: <key>` in the dataset entry. See [credentials](../configure/how_to_use_parameters_and_credentials.md).
- Configuration in `conf/local/` overrides `conf/base/`. Select another environment with `kedro run --env=<env>`. See [configuration](../configure/configuration_basics.md).

## CLI index

Run project commands from inside the project directory.

| Command                                                   | Use it to                                                                                                              |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `kedro new --name=<name> --tools=<tools> --example=<y/n>` | Create a project. `--tools` takes `lint,test,log,docs,data,pyspark`, `all`, or `none`.                                 |
| `kedro run`                                               | Run the `__default__` pipeline.                                                                                        |
| `kedro run --pipelines=<name1>,<name2>`                   | Run registered pipelines. `--pipeline` is deprecated.                                                                  |
| `kedro run --nodes=<node_name>`                           | Run named nodes. Also see `--from-nodes`, `--to-nodes`, `--from-inputs`, `--to-outputs`, `--tags`, and `--namespaces`. |
| `kedro run --params=<key1>=<value1>,<key2>=<value2>`      | Override parameters at runtime. Use `.` for nested keys.                                                               |
| `kedro run --runner=ThreadRunner`                         | Choose a runner.                                                                                                       |
| `kedro pipeline create <name>`                            | Scaffold a pipeline folder and its parameters file.                                                                    |
| `kedro registry list`                                     | List the pipelines in `pipeline_registry.py`.                                                                          |
| `kedro catalog describe-datasets`                         | Show which datasets a pipeline uses, grouped by type.                                                                  |
| `kedro catalog resolve-patterns`                          | Show how dataset factory patterns resolve for a pipeline.                                                              |
| `kedro jupyter lab`, `kedro ipython`                      | Start a notebook or shell with `catalog`, `context`, `pipelines`, and `session` loaded.                                |
| `kedro package`                                           | Build the project as a Python package.                                                                                 |
| `kedro info`                                              | Show the Kedro version and installed plugins.                                                                          |

Full reference: [Kedro CLI](commands_reference.md).

## Run a project from Python

```python
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

project_path = Path.cwd()  # replace with the path that contains pyproject.toml
bootstrap_project(project_path)
with KedroSession.create(project_path=project_path) as session:
    session.run(pipeline_names=["__default__"])
```

In a notebook, run `%load_ext kedro.ipython` from the project directory instead. See [Kedro and Jupyter notebooks](../integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks.md).

## Top errors and fixes

| Error                                                                                    | Cause                                                                                                                                                    | Fix                                                                                                                                                                                                |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ValueError: Pipeline input(s) {'<name>'} not found in the DataCatalog`                  | No node produces the input and the catalog has no entry for it. This also happens when you run part of a pipeline whose upstream outputs were in-memory. | Fix the dataset name, add a catalog entry, or persist the upstream output so a partial run can load it.                                                                                            |
| `DatasetError: Class '<type>' not found, is this a typo?`                                | The `type` has a typo, or `kedro-datasets` (or the extra for that dataset) is not installed.                                                             | Install the extra, for example `pip install "kedro-datasets[pandas-csvdataset]"`, and check the class name in the [kedro-datasets API](https://docs.kedro.org/projects/kedro-datasets/en/stable/). |
| `DatasetNotFoundError: Dataset '<name>' not found in the catalog`                        | Code asked the catalog for a name with no entry and no matching factory pattern.                                                                         | Add the entry to `catalog.yml`, or check the name with `kedro catalog describe-datasets`.                                                                                                          |
| `TypeError: Inputs of '<function>' function expected [...], but got ...`                 | The node's `inputs` do not match the function signature.                                                                                                 | Give one input per function argument, in order, or pass a dictionary that maps argument names to dataset names.                                                                                    |
| `OutputNotUniqueError: Output(s) [...] are returned by more than one nodes.`             | Two nodes write the same dataset name.                                                                                                                   | Give each output a unique name.                                                                                                                                                                    |
| `CircularDependencyError: Circular dependencies exist among the following ...`           | The nodes form a loop: an output feeds back into a node upstream of it.                                                                                  | Rename datasets so the graph has no cycle.                                                                                                                                                         |
| `RuntimeError: Could not find the project configuration file 'pyproject.toml' in <path>` | Kedro ran outside a project.                                                                                                                             | Run from the project directory, or pass `project_path` to `bootstrap_project` and `KedroSession.create`.                                                                                           |

## Tools for AI assistants

- [Kedro-MCP](../develop/vibe_coding_with_mcp.md): an MCP server that gives coding assistants curated Kedro instructions.
- [`kedro-skills`](../develop/vibe_coding_with_skills.md): context files that coding assistants load when you edit matching files in a Kedro project.
- [Inspection API](../inspect/inspect-project.md): a structured snapshot of a project's pipelines, nodes, datasets, and parameters.

## Where to go next

- [Kedro concepts](kedro_concepts.md): nodes, pipelines, the Data Catalog, and project structure.
- [Spaceflights tutorial](../tutorials/spaceflights_tutorial.md): a complete project, built step by step.
- [Kedro API reference](../api/index.md): generated reference for every public module.
- [`llms.txt`](https://docs.kedro.org/en/stable/llms.txt): the machine-readable index of these docs.
