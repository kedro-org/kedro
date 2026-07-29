# Kedro CLI cheatsheet

A quick reference for the most common [Kedro CLI](../getting-started/glossary.md#command-line-interface-cli) commands.
Run `kedro --help` or `kedro <command> --help` for full details.

## Global commands

These commands work from any directory.

| Command | Description |
|---------|-------------|
| `kedro info` | Show Kedro version and installed plugins. |
| `kedro new` | Create a new Kedro project from the default template. |
| `kedro starter list` | List available Kedro starters. |
| `kedro new --starter <name>` | Create a new project from a named starter. |

## Project commands

Run these from inside a Kedro project directory.

### Run pipelines

| Command | Description |
|---------|-------------|
| `kedro run` | Run the default pipeline. |
| `kedro run --pipeline <name>` | Run a specific pipeline. |
| `kedro run --nodes <node1>,<node2>` | Run only the specified nodes. |
| `kedro run --from-nodes <node>` | Run from a specific node onwards. |
| `kedro run --to-nodes <node>` | Run all nodes up to a specific node. |
| `kedro run --params key=value` | Override one or more parameters. |
| `kedro run --env <env>` | Run using a specific configuration environment. |
| `kedro run --runner <runner>` | Run with a specific runner, for example `ParallelRunner`. |

### Create project components

| Command | Description |
|---------|-------------|
| `kedro pipeline create <name>` | Create a new pipeline. |
| `kedro pipeline list` | List all pipelines in the project. |
| `kedro pipeline delete <name>` | Delete a pipeline. |
| `kedro pipeline package <name>` | Package a pipeline as a Python wheel. |
| `kedro pipeline pull <package>` | Pull a packaged pipeline into the project. |

### Inspect the project

| Command | Description |
|---------|-------------|
| `kedro catalog list` | List datasets defined in the Data Catalog. |
| `kedro catalog resolve-patterns` | Resolve dataset factory patterns. |
| `kedro catalog describe-datasets` | Describe datasets in the catalog. |
| `kedro registry list` | List all registered pipelines. |

### Package and deploy

| Command | Description |
|---------|-------------|
| `kedro package` | Build a Python wheel and package the project configuration. |
| `kedro server start` | Start the Kedro HTTP server. |

### Interactive development

| Command | Description |
|---------|-------------|
| `kedro ipython` | Launch an IPython session with the Kedro extension loaded. |
| `kedro jupyter notebook` | Launch Jupyter Notebook with the Kedro extension. |
| `kedro jupyter lab` | Launch JupyterLab with the Kedro extension. |

## Getting help

| Command | Description |
|---------|-------------|
| `kedro --help` | Show top-level help. |
| `kedro <command> --help` | Show help for a specific command. |
| `kedro <command> <subcommand> --help` | Show help for a specific subcommand. |

For more detail, see the [CLI command reference](../getting-started/commands_reference.md).
