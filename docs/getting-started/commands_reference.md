# Kedro's command line interface

Kedro's command line interface (CLI) is used to give commands to Kedro via a terminal shell (such as the terminal app on macOS, or cmd.exe or PowerShell on Windows). You need to use the CLI to set up a new Kedro project, and to run it.

## Autocompletion (optional)

If you are using macOS or Linux, you can set up your shell to autocomplete `kedro` commands. If you don't know the type of shell you are using, first type the following:

```bash
echo $0
```


=== "If you are using Bash"
    <br/>
    Add the following to your <code>~/.bashrc</code> (or just run it on the command line):

    ```bash
    eval "$(_KEDRO_COMPLETE=bash_source kedro)"
    ```


=== "If you are using Z shell (ZSh)"
    <br/>
    Add the following to <code>~/.zshrc</code>:

    ```bash
    eval "$(_KEDRO_COMPLETE=zsh_source kedro)"
    ```


=== "If you are using Fish"
    <br/>
    Add the following to <code>~/.config/fish/completions/foo-bar.fish</code>:

    ```bash
    eval (env _KEDRO_COMPLETE=fish_source kedro)
    ```


## Invoke Kedro CLI from Python (optional)
You can invoke the Kedro CLI as a Python module:

```bash
python -m kedro
```

## Kedro commands
Here is a list of Kedro CLI commands, as a shortcut to the descriptions below. Project-specific commands are called from within a project directory and apply to that particular project. Global commands can be run anywhere and don't apply to any particular project:


### Global Kedro commands
::: mkdocs-click
    :module: kedro.framework.cli.cli
    :command: global_commands
    :depth: 2
    :style: table

## Customise or override project-specific Kedro commands

!!! note
    All project related CLI commands should be run from the project’s root directory.

Kedro's command line interface (CLI) allows you to associate a set of commands and dependencies with a target, which you can then execute from inside the project directory.

The commands a project supports are specified on the framework side. If you want to customise any of the Kedro commands you can do this either by adding a file called `cli.py` or by injecting commands into it via the [`plugin` framework](../extend/plugins.md). Find the template for the `cli.py` file below.

### Project Kedro commands
::: mkdocs-click
    :module: kedro.framework.cli.cli
    :command: project_commands
    :depth: 2
    :style: table


### Project setup

#### Install all package dependencies

The following runs [`pip`](https://github.com/pypa/pip) to install all package dependencies specified in `requirements.txt`:

```bash
pip install -r requirements.txt
```

For further information, see the [documentation on installing project-specific dependencies](../develop/dependencies.md#install-project-specific-dependencies).


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
| `kedro run --nodes=<node_name1>,<node_name2>`                       | Run only nodes with specified names.                                                                                                                                                                                                                    |
| `kedro run --runner=<runner_name>`                                  | Run the pipeline with a specific runner                                                                                                                                                                                                                 |
| `kedro run --async`                                                 | Load and save node inputs and outputs asynchronously with threads                                                                                                                                                                                       |
| `kedro run --env=<env_name>`                                        | Run the pipeline in the env_name environment. Defaults to local if not provided                                                                                                                                                                         |
| `kedro run --tags=<tag_name1>,<tag_name2>`                          | Run only nodes which have any of these tags attached.                                                                                                                                                                                                   |
| `kedro run --load-versions=<dataset_name>:YYYY-MM-DDThh.mm.ss.sssZ` | Specify particular dataset versions (timestamp) for loading.                                                                                                                                                                                            |
| `kedro run --pipeline=<pipeline_name>`                              | Run the whole pipeline by its name                                                                                                                                                                                                                      |
| `kedro run --namespaces=<namespace>`                                 | Run only nodes with the specified namespace                                                                                                                                                                                                             |
| `kedro run --config=<config_file_name>.yml`                         | Specify all command line options in a named YAML configuration file                                                                                                                                                                                     |
| `kedro run --conf-source=<path_to_config_directory>`                | Specify a new source directory for configuration files                                                                                                                                                                                                  |
| `kedro run --conf-source=<path_to_compressed file>`                 | Only possible when using the [``OmegaConfigLoader``](../configure/configuration_basics.md#omegaconfigloader). Specify a compressed config file in `zip` or `tar` format.                                                                            |
| `kedro run --params=<param_key1>=<value1>,<param_key2>=<value2>`    | Does a parametrised run with `{"param_key1": "value1", "param_key2": 2}`. These will take precedence over parameters defined in the `conf` directory. Additionally, dot (`.`) syntax can be used to address nested keys like `parent.child:value` |
| `kedro run --only-missing-outputs`                                  | Run only the nodes required to produce missing persistent outputs. If a node's persistent outputs already exist, the node and its upstream dependencies (if not needed for other missing outputs) will be skipped.                                      |

You can also combine these options together, so the following command runs all the nodes from `split` to `predict` and `report`:

```bash
kedro run --from-nodes=split --to-nodes=predict,report
```

This functionality is extended to the `kedro run --config=config.yml` command, which allows you to [specify run commands in a configuration file](../build/run_a_pipeline.md#configure-kedro-run-arguments).

A parameterised run is best used for dynamic parameters, i.e. running the same pipeline with different inputs, for static parameters that do not change we recommend following the [Kedro project setup methodology](../configure/parameters.md).

### Deploy the project

The following packages your application as one `.whl` file within the `dist/` folder of your project. It packages the project configuration separately in a `tar.gz` file:

```bash
kedro package
```

See [the Python documentation for further information about packaging](https://packaging.python.org/overview/).

### Project quality

### Project development

#### Modular pipelines

##### Create a new [modular pipeline](../build/modular_pipelines.md) in your project

```bash
kedro pipeline create <pipeline_name>
```

##### Delete a modular pipeline
The following command deletes all the files related to a modular pipeline in your Kedro project.

```bash
kedro pipeline delete <pipeline_name>
```

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

#### Data Catalog

##### Lists all datasets used in the specified pipelines

This command lists all datasets used in the specified pipeline(s), grouped by how they are defined.

- datasets: Explicitly defined in catalog.yml
- factories: Resolved using dataset factory patterns
- defaults: Handled by user catch-all or default runtime patterns

```bash
kedro catalog list-datasets
```

The command also accepts an optional `--pipeline` argument that allows you to specify the pipeline name(s) (comma-separated values) in order to filter datasets used only by those named pipeline(s). For example:

```bash
kedro catalog list-datasets --pipeline=ds,de
```

!!! note
    If no pipelines are specified, the `__default__` pipeline is used.

##### Resolve dataset factories in the catalog

This command resolves datasets used in the pipeline against all dataset patterns, returning their full catalog configuration. It includes datasets explicitly defined in the catalog as well as those resolved from dataset factory patterns.

```bash
kedro catalog resolve-patterns
```

The command also accepts an optional `--pipeline` argument that allows you to specify the pipeline name(s) (comma-separated values).

```bash
kedro catalog resolve-patterns --pipeline=ds,de
```

!!! note
    If no pipelines are specified, the `__default__` pipeline is used.

##### List all dataset factory patterns defined in the catalog ordered by priority

```bash
kedro catalog list-patterns
```

The output includes a list of any [dataset factories](../catalog-data/kedro_dataset_factories.md) in the catalog, ranked by the priority on which they are matched against.

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

The [Kedro IPython extension](../integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks.md#what-does-kedro-jupyter-notebook-do) makes the following variables available in your IPython or Jupyter session:

* `catalog` (type [kedro.io.DataCatalog][]): [Data Catalog](../catalog-data/data_catalog.md) instance that contains all defined datasets; this is a shortcut for `context.catalog`
* `context` (type [kedro.framework.context.KedroContext][]): Kedro project context that provides access to Kedro's library components
* `pipelines` (type `dict[str, Pipeline]`): Pipelines defined in your [pipeline registry](../build/run_a_pipeline.md#run-a-pipeline-by-name)
* `session` (type [kedro.framework.session.session.KedroSession][]): [Kedro session](../extend/session.md) that orchestrates a pipeline run

To reload these variables (e.g. if you updated `catalog.yml`) use the `%reload_kedro` line magic, which can also be used to see the error message if any of the variables above are undefined.
