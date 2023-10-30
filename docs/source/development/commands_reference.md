# Kedro's command line interface

Kedro's command line interface (CLI) is used to give commands to Kedro via a terminal shell (such as the terminal app on macOS, or cmd.exe or PowerShell on Windows). You need to use the CLI to set up a new Kedro project, and to run it.

## Autocompletion (optional)

If you are using macOS or Linux, you can set up your shell to autocomplete `kedro` commands. If you don't know the type of shell you are using, first type the following:

```bash
echo $0
```

<details>
<summary>If you are using Bash (click to expand)</summary>
<br/>
Add the following to your <code>~/.bashrc</code> (or just run it on the command line):

```bash
eval "$(_KEDRO_COMPLETE=source kedro)"
```
</details>

<details>
<summary>If you are using Z shell (ZSh) (click to expand)</summary>
<br/>
Add the following to <code>~/.zshrc</code>:

```bash
eval "$(_KEDRO_COMPLETE=source_zsh kedro)"
```
</details>

<details>
<summary>If you are using Fish (click to expand)</summary>
<br/>
Add the following to <code>~/.config/fish/completions/foo-bar.fish</code>:

```bash
eval (env _KEDRO_COMPLETE=source_fish kedro)
```
</details>

## Invoke Kedro CLI from Python (optional)
You can invoke the Kedro CLI as a Python module:

```bash
python -m kedro
```

## Kedro commands
Here is a list of Kedro CLI commands, as a shortcut to the descriptions below. Project-specific commands are called from within a project directory and apply to that particular project. Global commands can be run anywhere and don't apply to any particular project:

* Global Kedro commands
  * [`kedro --help`](#get-help-on-kedro-commands)
  * [`kedro --version`](#confirm-the-kedro-version)
  * [`kedro info`](#confirm-kedro-information)
  * [`kedro new`](#create-a-new-kedro-project)

* Project-specific Kedro commands
  * [`kedro catalog list`](#list-datasets-per-pipeline-per-type)
  * [`kedro catalog resolve`](#resolve-dataset-factories-in-the-catalog)
  * [`kedro catalog rank`](#rank-dataset-factories-in-the-catalog)
  * [`kedro catalog create`](#create-a-data-catalog-yaml-configuration-file)
  * [`kedro ipython`](#notebooks)
  * [`kedro jupyter lab`](#notebooks)
  * [`kedro jupyter notebook`](#notebooks)
  * [`kedro micropkg package <pipeline_name>`](#package-a-micro-package)
  * [`kedro micropkg pull <package_name>`](#pull-a-micro-package)
  * [`kedro package`](#deploy-the-project)
  * [`kedro pipeline create <pipeline_name>`](#create-a-new-modular-pipeline-in-your-project)
  * [`kedro pipeline delete <pipeline_name>`](#delete-a-modular-pipeline)
  * [`kedro registry describe <pipeline_name>`](#describe-a-registered-pipeline)
  * [`kedro registry list`](#list-all-registered-pipelines-in-your-project)
  * [`kedro run`](#run-the-project)

## Global Kedro commands

The following are Kedro commands that apply globally and can be run from any directory location.

```{note}
You only need to use one of those given below (e.g. specify `kedro -V` **OR** `kedro --version`).
```

### Get help on Kedro commands

```bash
kedro
kedro -h
kedro --help
```

### Confirm the Kedro version

```bash
kedro -V
kedro --version
```

### Confirm Kedro information

```bash
kedro info
```
Returns output similar to the following, depending on the version of Kedro used and plugins installed.

```
 _            _
| | _____  __| |_ __ ___
| |/ / _ \/ _` | '__/ _ \
|   <  __/ (_| | | | (_) |
|_|\_\___|\__,_|_|  \___/
v0.18.14

Kedro is a Python framework for
creating reproducible, maintainable
and modular data science code.

Installed plugins:
kedro_viz: 4.4.0 (hooks:global,line_magic)

```

### Create a new Kedro project

```bash
kedro new
```

## Customise or Override Project-specific Kedro commands

```{note}
All project related CLI commands should be run from the project’s root directory.
```

Kedro's command line interface (CLI) allows you to associate a set of commands and dependencies with a target, which you can then execute from inside the project directory.

The commands a project supports are specified on the framework side. If you want to customise any of the Kedro commands you can do this either by adding a file called `cli.py` or by injecting commands into it via the [`plugin` framework](../extend_kedro/plugins.md). Find the template for the `cli.py` file below.

<details>
<summary><b>Click to expand</b></summary>

```
"""Command line tools for manipulating a Kedro project.
Intended to be invoked via `kedro`."""
import click
from kedro.framework.cli.project import (
    ASYNC_ARG_HELP,
    CONFIG_FILE_HELP,
    CONF_SOURCE_HELP,
    FROM_INPUTS_HELP,
    FROM_NODES_HELP,
    LOAD_VERSION_HELP,
    NODE_ARG_HELP,
    PARAMS_ARG_HELP,
    PIPELINE_ARG_HELP,
    RUNNER_ARG_HELP,
    TAG_ARG_HELP,
    TO_NODES_HELP,
    TO_OUTPUTS_HELP,
    project_group,
)
from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    _config_file_callback,
    _get_values_as_tuple,
    _reformat_load_versions,
    _split_params,
    env_option,
    split_string,
    split_node_names,
)
from kedro.framework.session import KedroSession
from kedro.utils import load_obj


@click.group(context_settings=CONTEXT_SETTINGS, name=__file__)
def cli():
    """Command line tools for manipulating a Kedro project."""


@project_group.command()
@click.option(
    "--from-inputs", type=str, default="", help=FROM_INPUTS_HELP, callback=split_string
)
@click.option(
    "--to-outputs", type=str, default="", help=TO_OUTPUTS_HELP, callback=split_string
)
@click.option(
    "--from-nodes", type=str, default="", help=FROM_NODES_HELP, callback=split_node_names
)
@click.option(
    "--to-nodes", type=str, default="", help=TO_NODES_HELP, callback=split_node_names
)
@click.option("--node", "-n", "node_names", type=str, multiple=True, help=NODE_ARG_HELP)
@click.option(
    "--runner", "-r", type=str, default=None, multiple=False, help=RUNNER_ARG_HELP
)
@click.option("--async", "is_async", is_flag=True, multiple=False, help=ASYNC_ARG_HELP)
@env_option
@click.option("--tag", "-t", type=str, multiple=True, help=TAG_ARG_HELP)
@click.option(
    "--load-version",
    "-lv",
    type=str,
    multiple=True,
    help=LOAD_VERSION_HELP,
    callback=_reformat_load_versions,
)
@click.option("--pipeline", "-p", type=str, default=None, help=PIPELINE_ARG_HELP)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help=CONFIG_FILE_HELP,
    callback=_config_file_callback,
)
@click.option(
    "--conf-source",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help=CONF_SOURCE_HELP,
)
@click.option(
    "--params",
    type=click.UNPROCESSED,
    default="",
    help=PARAMS_ARG_HELP,
    callback=_split_params,
)
def run(
    tag,
    env,
    runner,
    is_async,
    node_names,
    to_nodes,
    from_nodes,
    from_inputs,
    to_outputs,
    load_version,
    pipeline,
    config,
    conf_source,
    params,
):
    """Run the pipeline."""

    ##### ADD YOUR CUSTOM RUN COMMAND CODE HERE #####
    runner = load_obj(runner or "SequentialRunner", "kedro.runner")

    tag = _get_values_as_tuple(tag) if tag else tag
    node_names = _get_values_as_tuple(node_names) if node_names else node_names

    with KedroSession.create(
        env=env, conf_source=conf_source, extra_params=params
    ) as session:
        session.run(
            tags=tag,
            runner=runner(is_async=is_async),
            node_names=node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_version,
            pipeline_name=pipeline,
        )


```
</details>

### Project setup

#### Install all package dependencies

The following runs [`pip`](https://github.com/pypa/pip) to install all package dependencies specified in `requirements.txt`:

```bash
pip install -r requirements.txt
```

For further information, see the [documentation on installing project-specific dependencies](../kedro_project_setup/dependencies.md#install-project-specific-dependencies).


### Run the project
Call the `run()` method of the `KedroSession` defined in `kedro.framework.session`.

```bash
kedro run
```

`KedroContext` can be extended in `run.py` (`src/<package_name>/run.py`). In order to use the extended `KedroContext`, you need to set `context_path` in the `pyproject.toml` configuration file.

#### Modifying a `kedro run`

Kedro has options to modify pipeline runs. Below is a list of CLI arguments supported out of the box. Note that the names inside angular brackets (`<>`) are placeholders, and you should replace these values with the
the names of relevant nodes, datasets, envs, etc. in your project.

| CLI command                                                         | Description                                                                                                                                                                                                                                             |
|---------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `kedro run --from-inputs=<dataset_name1>,<dataset_name2>`           | A list of dataset names which should be used as a starting point                                                                                                                                                                                        |
| `kedro run --to-outputs=<dataset_name1>,<dataset_name2>`            | A list of dataset names which should be used as an end point                                                                                                                                                                                            |
| `kedro run --from-nodes=<node_name1>,<node_name2>`                  | A list of node names which should be used as a starting point                                                                                                                                                                                           |
| `kedro run --to-nodes=<node_name1>,<node_name1>`                    | A list of node names which should be used as an end point                                                                                                                                                                                               |
| [DEPRECATED] `kedro run --node=<node_name1>,<node_name2>`           | Run only nodes with specified names. <br /> Multiple instances allowed. <br /> NOTE: This flag will be deprecated in `Kedro 0.19.0`. Use the following flag `--nodes` instead.                                                                          |
| `kedro run --nodes=<node_name1>,<node_name2>`                       | Run only nodes with specified names.                                                                                                                                                                                                                    |
| `kedro run --runner=<runner_name>`                                  | Run the pipeline with a specific runner                                                                                                                                                                                                                 |
| `kedro run --async`                                                 | Load and save node inputs and outputs asynchronously with threads                                                                                                                                                                                       |
| `kedro run --env=<env_name>`                                        | Run the pipeline in the env_name environment. Defaults to local if not provided                                                                                                                                                                         |
| [DEPRECATED] `kedro run --tag=<tag_name1>,<tag_name2>`              | Run only nodes which have any of these tags attached. <br /> Multiple instances allowed. <br /> NOTE: This flag will be deprecated in `Kedro 0.19.0`. Use the following flag `--tags` instead.                                                                                                                                                                 |
| `kedro run --tags=<tag_name1>,<tag_name2>`                          | Run only nodes which have any of these tags attached.                                                                                            |
| [DEPRECATED] `kedro run --load-version=<dataset_name>:YYYY-MM-DDThh.mm.ss.sssZ`  | Specify a particular dataset version (timestamp) for loading. <br /> Multiple instances allowed. <br /> NOTE: This flag will be deprecated in `Kedro 0.19.0`. Use the following flag `--load-versions` instead.                            |
| `kedro run --load-versions=<dataset_name>:YYYY-MM-DDThh.mm.ss.sssZ` | Specify particular dataset versions (timestamp) for loading.                                                                                                                                                                                            |
| `kedro run --pipeline=<pipeline_name>`                              | Run the whole pipeline by its name                                                                                                                                                                                                                      |
| `kedro run --namespace=<namespace>`                                 | Run only nodes with the specified namespace                                                                                                                                                                                                             |
| `kedro run --config=<config_file_name>.yml`                         | Specify all command line options in a named YAML configuration file                                                                                                                                                                                     |
| `kedro run --conf-source=<path_to_config_directory>`                | Specify a new source directory for configuration files                                                                                                                                                                                                  |
| `kedro run --conf-source=<path_to_compressed file>`                 | Only possible when using the [``OmegaConfigLoader``](../configuration/advanced_configuration.md#omegaconfigloader). Specify a compressed config file in `zip` or `tar` format.                                                                  |
| `kedro run --params=<param_key1>:<value1>,<param_key2>:<value2>`    | Does a parametrised kedro run with `{"param_key1": "value1", "param_key2": 2}`. These will take precedence over parameters defined in the `conf` directory. Additionally, dot (`.`) syntax can be used to address nested keys like `parent.child:value` |

You can also combine these options together, so the following command runs all the nodes from `split` to `predict` and `report`:

```bash
kedro run --from-nodes=split --to-nodes=predict,report
```

This functionality is extended to the `kedro run --config=config.yml` command, which allows you to [specify run commands in a configuration file](../nodes_and_pipelines/run_a_pipeline.md#configure-kedro-run-arguments).

A parameterised run is best used for dynamic parameters, i.e. running the same pipeline with different inputs, for static parameters that do not change we recommend following the [Kedro project setup methodology](../configuration/parameters.md).

### Deploy the project

The following packages your application as one `.whl` file within the `dist/` folder of your project. It packages the project configuration separately in a `tar.gz` file:

```bash
kedro package
```

See [the Python documentation for further information about packaging](https://packaging.python.org/overview/).

### Pull a micro-package
Since Kedro 0.17.7 you can pull a micro-package into your Kedro project as follows:

```bash
kedro micropkg pull <link-to-micro-package-sdist-file>
```

The above command will take the bundled `.tar.gz` file and do the following:

* Place source code in `src/<package_name>/pipelines/<pipeline_name>`
* Place parameters in `conf/base/parameters_<pipeline_name>.yml`
* Pull out tests and place in `src/tests/pipelines/<pipeline_name>`

`kedro micropkg pull` works with PyPI, local and cloud storage:

* PyPI: `kedro micropkg pull <my-pipeline>` with `<my-pipeline>` being a package on PyPI
* Local storage: `kedro micropkg pull dist/<my-pipeline>-0.1.tar.gz`
* Cloud storage: `kedro micropkg pull s3://<my-bucket>/<my-pipeline>-0.1.tar.gz`

### Project quality

### Project development

#### Modular pipelines

##### Create a new [modular pipeline](../nodes_and_pipelines/modular_pipelines) in your project

```bash
kedro pipeline create <pipeline_name>
```

##### Package a micro-package
The following command packages all the files related to a micro-package, e.g. a modular pipeline, into a [Python source distribution file](https://packaging.python.org/overview/#python-source-distributions):

```bash
kedro micropkg package <package_module_path>
```

Further information is available in the [micro-packaging documentation](../nodes_and_pipelines/micro_packaging.md).

##### Pull a micro-package in your project
The following command pulls all the files related to a micro-package, e.g. a modular pipeline, from either [PyPI](https://pypi.org/) or a storage location of a [Python source distribution file](https://packaging.python.org/overview/#python-source-distributions).

```bash
kedro micropkg pull <package_name> (or path to a sdist file)
```

Further information is available in [the micro-packaging documentation](../nodes_and_pipelines/micro_packaging.md).

##### Delete a modular pipeline
The following command deletes all the files related to a modular pipeline in your Kedro project.

```bash
kedro pipeline delete <pipeline_name>
```

Further information is available in [the micro-packaging documentation](../nodes_and_pipelines/micro_packaging.md).

#### Registered pipelines

##### Describe a registered pipeline

```bash
kedro registry describe <pipeline_name>
```
The output includes all the nodes in the pipeline. If no pipeline name is provided, this command returns all nodes in the `__default__` pipeline.

##### List all registered pipelines in your project

```bash
kedro registry list
```

#### Datasets

##### List datasets per pipeline per type

```bash
kedro catalog list
```
The results include datasets that are/aren't used by a specific pipeline.

The command also accepts an optional `--pipeline` argument that allows you to specify the pipeline name(s) (comma-separated values) in order to filter datasets used only by those named pipeline(s). For example:

```bash
kedro catalog list --pipeline=ds,de
```

##### Resolve dataset factories in the catalog

```bash
kedro catalog resolve
```

This command resolves dataset factories in the catalog file with any explicit entries in the pipeline. The output includes datasets explicitly mentioned in your catalog files and any datasets mentioned in the project's pipelines that match a dataset factory.

##### Rank dataset factories in the catalog

```bash
kedro catalog rank
```

The output includes a list of any [dataset factories](../data/kedro_dataset_factories.md) in the catalog, ranked by the priority on which they are matched against.

#### Data Catalog

##### Create a Data Catalog YAML configuration file

The following command creates a Data Catalog YAML configuration file with `MemoryDataset` datasets for each dataset in a registered pipeline, if it is missing from the `DataCatalog`.

```bash
kedro catalog create --pipeline=<pipeline_name>
```

The command also accepts an optional `--env` argument that allows you to specify a configuration environment (defaults to `base`).

The command creates the following file: `<conf_root>/<env>/catalog_<pipeline_name>.yml`

#### Notebooks

To start a Jupyter Notebook:

```bash
kedro jupyter notebook
```

To start JupyterLab:

```bash
kedro jupyter lab
```

To start an IPython shell:

```bash
kedro ipython
```

The [Kedro IPython extension](../notebooks_and_ipython/kedro_and_notebooks.md#what-does-kedro-jupyter-notebook-do) makes the following variables available in your IPython or Jupyter session:

* `catalog` (type `DataCatalog`): [Data Catalog](../data/data_catalog.md) instance that contains all defined datasets; this is a shortcut for `context.catalog`
* `context` (type `KedroContext`): Kedro project context that provides access to Kedro's library components
* `pipelines` (type `Dict[str, Pipeline]`): Pipelines defined in your [pipeline registry](../nodes_and_pipelines/run_a_pipeline.md#run-a-pipeline-by-name)
* `session` (type `KedroSession`): [Kedro session](../kedro_project_setup/session.md) that orchestrates a pipeline run

To reload these variables (e.g. if you updated `catalog.yml`) use the `%reload_kedro` line magic, which can also be used to see the error message if any of the variables above are undefined.
