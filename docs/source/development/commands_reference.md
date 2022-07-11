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
  * [`kedro activate-nbstripout`](#strip-output-cells)
  * [`kedro build-docs`](#build-the-project-documentation)
  * [`kedro build-reqs`](#build-the-projects-dependency-tree)
  * [`kedro catalog list`](#list-datasets-per-pipeline-per-type)
  * [`kedro catalog create`](#create-a-data-catalog-yaml-configuration-file)
  * [`kedro ipython`](#notebooks)
  * [`kedro jupyter convert`](#copy-tagged-cells)
  * [`kedro jupyter lab`](#notebooks)
  * [`kedro jupyter notebook`](#notebooks)
  * [`kedro lint`](#lint-your-project)
  * [`kedro micropkg package <pipeline_name>`](#package-a-micro-package)
  * [`kedro micropkg pull <package_name>`](#pull-a-micro-package)
  * [`kedro package`](#deploy-the-project)
  * [`kedro pipeline create <pipeline_name>`](#create-a-new-modular-pipeline-in-your-project)
  * [`kedro pipeline delete <pipeline_name>`](#delete-a-modular-pipeline)
  * [`kedro registry describe <pipeline_name>`](#describe-a-registered-pipeline)
  * [`kedro registry list`](#list-all-registered-pipelines-in-your-project)
  * [`kedro run`](#run-the-project)
  * [`kedro test`](#test-your-project)

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
v0.18.2

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
    "--from-nodes", type=str, default="", help=FROM_NODES_HELP, callback=split_string
)
@click.option(
    "--to-nodes", type=str, default="", help=TO_NODES_HELP, callback=split_string
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
    "--params",
    type=click.UNPROCESSED,
    default="",
    help=PARAMS_ARG_HELP,
    callback=_split_params,
)
# pylint: disable=too-many-arguments,unused-argument
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
    params,
):
    """Run the pipeline."""

    ##### ADD YOUR CUSTOM RUN COMMAND CODE HERE #####
    runner = load_obj(runner or "SequentialRunner", "kedro.runner")

    tag = _get_values_as_tuple(tag) if tag else tag
    node_names = _get_values_as_tuple(node_names) if node_names else node_names

    with KedroSession.create(env=env, extra_params=params) as session:
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

#### Build the project's dependency tree

```bash
kedro build-reqs
```

This command runs [`pip-compile`](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) on the project's `src/requirements.txt` file and will create `src/requirements.lock` with the compiled requirements.

`kedro build-reqs` has two optional arguments to specify which file to compile the requirements from and where to save the compiled requirements to. These arguments are `--input-file` and `--output-file` respectively.

`kedro build-reqs` also accepts and passes through CLI options accepted by `pip-compile`. For example, `kedro build-reqs --generate-hashes` will call `pip-compile --output-file=src/requirements.lock --generate-hashes src/requirements.txt`.

#### Install all package dependencies

The following runs [`pip`](https://github.com/pypa/pip) to install all package dependencies specified in `src/requirements.txt`:

```bash
pip install -r src/requirements.txt
```

For further information, see the [documentation on installing project-specific dependencies](../kedro_project_setup/dependencies.md#install-project-specific-dependencies).


### Run the project
Call the `run()` method of the `KedroSession` defined in `kedro.framework.session`.

```bash
kedro run
```

`KedroContext` can be extended in `run.py` (`src/<package_name>/run.py`). In order to use the extended `KedroContext`, you need to set `context_path` in the [`pyproject.toml` configuration file](../faq/architecture_overview.md#kedro-project).

#### Modifying a `kedro run`

Kedro has options to modify pipeline runs. Here is a list of CLI arguments supported out of the box:

| CLI command                                                         | Description                                                                                                                                                                                                                                             | Multiple instances allowed? |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `kedro run --from-inputs dataset1,dataset2`                         | A list of dataset names which should be used as a starting point                                                                                                                                                                                        | No                          |
| `kedro run --from-nodes node1,node2`                                | A list of node names which should be used as a starting point                                                                                                                                                                                           | No                          |
| `kedro run --to-nodes node3,node4`                                  | A list of node names which should be used as an end point                                                                                                                                                                                               | No                          |
| `kedro run --node debug_me,debug_me_too`                            | Run only nodes with specified names                                                                                                                                                                                                                     | Yes                         |
| `kedro run --runner runner_name`                                    | Run the pipeline with a specific runner                                                                                                                                                                                                                 | No                          |
| `kedro run --env env_name`                                          | Run the pipeline in the env_name environment. Defaults to local if not provided                                                                                                                                                                         | No                          |
| `kedro run --tag some_tag1,some_tag2`                               | Run only nodes which have any of these tags attached                                                                                                                                                                                                    | Yes                         |
| `kedro run --load-version="some_dataset:YYYY-MM-DDThh.mm.ss.sssZ"`  | Specify a particular dataset version (timestamp) for loading                                                                                                                                                                                            | Yes                         |
| `kedro run --pipeline de`                                           | Run the whole pipeline by its name                                                                                                                                                                                                                      | No                          |
| `kedro run --config config.yml`                                     | Specify all command line options in a configuration file called config.yml                                                                                                                                                                              | No                          |
| `kedro run --params param_key1:value1,param_key2:2.0`               | Does a parametrised kedro run with `{"param_key1": "value1", "param_key2": 2}`. These will take precedence over parameters defined in the `conf` directory. Additionally, dot (`.`) syntax can be used to address nested keys like `parent.child:value` | Yes                         |

You can also combine these options together, so the following command runs all the nodes from `split` to `predict` and `report`:

```bash
kedro run --from-nodes split --to-nodes predict,report
```

This functionality is extended to the `kedro run --config config.yml` command, which allows you to [specify run commands in a configuration file](../kedro_project_setup/configuration.md#configure-kedro-run-arguments).

A parameterised run is best used for dynamic parameters, i.e. running the same pipeline with different inputs, for static parameters that do not change we recommend following the [Kedro project setup methodology](../kedro_project_setup/configuration.md#parameters).

### Deploy the project

The following packages your application as one `.egg` file  and one `.whl` file within the `dist/` folder of your project:

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
* Place parameters in `conf/base/parameters/<pipeline_name>.yml`
* Pull out tests and place in `src/tests/pipelines/<pipeline_name>`

`kedro micropkg pull` works with PyPI, local and cloud storage:

* PyPI: `kedro micropkg pull <my-pipeline>` with `<my-pipeline>` being a package on PyPI
* Local storage: `kedro micropkg pull <path-to-your-project-root>/dist/<my-pipeline>-0.1.tar.gz`
* Cloud storage: `kedro micropkg pull s3://<my-bucket>/<my-pipeline>-0.1.tar.gz`

### Project quality

#### Build the project documentation

```bash
kedro build-docs
```

The `build-docs` command builds [project documentation](../tutorial/package_a_project.md#add-documentation-to-your-project) using the [Sphinx](https://www.sphinx-doc.org) framework. To further customise your documentation, please refer to `docs/source/conf.py` and the [Sphinx documentation](http://www.sphinx-doc.org/en/master/usage/configuration.html).


#### Lint your project

```bash
kedro lint
```

Your project is linted with [`black`](https://github.com/psf/black), [`flake8`](https://gitlab.com/pycqa/flake8) and [`isort`](https://github.com/PyCQA/isort).


#### Test your project

The following runs all `pytest` unit tests found in `src/tests`, including coverage (see the file `.coveragerc`):

```bash
kedro test
```

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
The following command pulls all the files related to a micro-package, e.g. a modular pipeline, from either [Pypi](https://pypi.org/) or a storage location of a [Python source distribution file](https://packaging.python.org/overview/#python-source-distributions).

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
kedro catalog list --pipeline "ds,de"
```

#### Data Catalog

##### Create a Data Catalog YAML configuration file

The following command creates a Data Catalog YAML configuration file with `MemoryDataSet` datasets for each dataset in a registered pipeline, if it is missing from the `DataCatalog`.

```bash
kedro catalog create --pipeline <pipeline_name>
```

The command also accepts an optional `--env` argument that allows you to specify a configuration environment (defaults to `base`).

The command creates the following file: `<conf_root>/<env>/catalog/<pipeline_name>.yml`

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

Every time you start or restart a notebook kernel, a startup script (`<project-root>/.ipython/profile_default/startup/00-kedro-init.py`) will add the following variables in scope:

- `context`: An instance of `kedro.framework.context.KedroContext` class or custom context class extending `KedroContext` if one was set to `CONTEXT_CLASS` in `settings.py` file (further details of how to use `context` can be found [in the IPython documentation](../tools_integration/ipython.md))
- `startup_error` (`Exception`)
- `catalog`

To reload these variables at any point in your notebook (e.g. if you updated `catalog.yml`) use the [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html#line-magics) `%reload_kedro`, which can be also used to see the error message if any of the variables above are undefined.

If you get an error message `Module ``<module_name>`` not found. Make sure to install required project dependencies by running ``pip install -r requirements.txt`` first.` when running any of those commands, it indicates that some Jupyter or IPython dependencies are not installed in your environment. To resolve this you will need to do the following:

1. Make sure the corresponding dependency is present in `src/requirements.txt`
2. Run [`pip install -r src/requirements.txt`](#install-all-package-dependencies) command from your terminal

##### Copy tagged cells
To copy the code from [cells tagged](https://jupyter-notebook.readthedocs.io/en/stable/changelog.html#cell-tags) with a `node` tag into Python files under `src/<package_name>/nodes/` in a Kedro project:

```bash
kedro jupyter convert --all
```

##### Strip output cells
Output cells of Jupyter Notebook should not be tracked by git, especially if they contain sensitive information. To strip them out:

```bash
kedro activate-nbstripout
```

This command adds a `git hook` which clears all notebook output cells before committing anything to `git`. It needs to run only once per local repository.
