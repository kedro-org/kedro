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
Kedro provides a set of CLI commands, which are automatically grouped and documented below using their inline docstrings.

- **Global commands** can be run from anywhere and are not tied to any specific Kedro project.
- **Project commands** must be run from within a Kedro project directory and apply only to that project.

### Global Kedro commands
::: mkdocs-click
    :module: kedro.framework.cli.cli
    :command: global_commands
    :depth: 2
    :style: plain


### Project Kedro commands
::: mkdocs-click
    :module: kedro.framework.cli.cli
    :command: project_commands
    :depth: 2
    :style: plain

## Customise or override project-specific Kedro commands

!!! note
    All project related CLI commands should be run from the project’s root directory.

Kedro's command line interface (CLI) allows you to associate a set of commands and dependencies with a target, which you can then execute from inside the project directory.

The commands a project supports are specified on the framework side. If you want to customise any of the Kedro commands you can do this either by adding a file called `cli.py` or by injecting commands into it via the [`plugin` framework](../extend/plugins.md). Find the template for the `cli.py` file below.

??? example "View code"
    ```python
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
    )
    from kedro.framework.cli.utils import (
        CONTEXT_SETTINGS,
        _config_file_callback,
        _split_params,
        _split_load_versions,
        env_option,
        split_string,
        split_node_names,
    )
    from kedro.framework.session import KedroSession
    from kedro.utils import load_obj


    @click.group(context_settings=CONTEXT_SETTINGS, name=__file__)
    def cli():
        """Command line tools for manipulating a Kedro project."""
    @cli.command()

    @click.option(
        "--from-inputs",
        type=str,
        default="",
        help=FROM_INPUTS_HELP,
        callback=split_string,
    )
    @click.option(
        "--to-outputs",
        type=str,
        default="",
        help=TO_OUTPUTS_HELP,
        callback=split_string,
    )
    @click.option(
        "--from-nodes",
        type=str,
        default="",
        help=FROM_NODES_HELP,
        callback=split_node_names,
    )
    @click.option(
        "--to-nodes", type=str, default="", help=TO_NODES_HELP, callback=split_node_names
    )
    @click.option(
        "--nodes",
        "-n",
        "node_names",
        type=str,
        default="",
        help=NODE_ARG_HELP,
        callback=split_node_names,
    )
    @click.option("--runner", "-r", type=str, default=None, help=RUNNER_ARG_HELP)
    @click.option("--async", "is_async", is_flag=True, help=ASYNC_ARG_HELP)
    @env_option
    @click.option(
        "--tags",
        "-t",
        type=str,
        default="",
        help=TAG_ARG_HELP,
        callback=split_string,
    )
    @click.option(
        "--load-versions",
        "-lv",
        type=str,
        default="",
        help=LOAD_VERSION_HELP,
        callback=_split_load_versions,
    )
    @click.option("--pipeline", "-p", type=str, default=None, help=PIPELINE_ARG_HELP)
    @click.option(
        "--namespaces",
        "-ns",
        type=str,
        default="",
        help=NAMESPACES_ARG_HELP,
        callback=split_node_names,
    )
    @click.option(
        "--config",
        "-c",
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        help=CONFIG_FILE_HELP,
        callback=_config_file_callback,
    )
    @click.option(
        "--conf-source",
        callback=validate_conf_source,
        help=CONF_SOURCE_HELP,
    )
    @click.option(
        "--params",
        type=click.UNPROCESSED,
        default="",
        help=PARAMS_ARG_HELP,
        callback=_split_params,
    )
    @click.option(
        "--only-missing-outputs",
        is_flag=True,
        help=ONLY_MISSING_OUTPUTS_HELP,
    )
    def run(
        tags: str,
        env: str,
        runner: str,
        is_async: bool,
        node_names: str,
        to_nodes: str,
        from_nodes: str,
        from_inputs: str,
        to_outputs: str,
        load_versions: dict[str, str] | None,
        pipeline: str,
        config: str,
        conf_source: str,
        params: dict[str, Any],
        namespaces: str,
        only_missing_outputs: bool,
    ) -> dict[str, Any]:
        """Run the pipeline."""

        runner_obj = load_obj(runner or "SequentialRunner", "kedro.runner")
        tuple_tags = tuple(tags)
        tuple_node_names = tuple(node_names)

        with KedroSession.create(
            env=env, conf_source=conf_source, runtime_params=params
        ) as session:
            return session.run(
                tags=tuple_tags,
                runner=runner_obj(is_async=is_async),
                node_names=tuple_node_names,
                from_nodes=from_nodes,
                to_nodes=to_nodes,
                from_inputs=from_inputs,
                to_outputs=to_outputs,
                load_versions=load_versions,
                pipeline_name=pipeline,
                namespaces=namespaces,
                only_missing_outputs=only_missing_outputs,
            )
