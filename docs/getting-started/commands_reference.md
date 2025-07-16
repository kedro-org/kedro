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
    :style: plain

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
    :style: plain
