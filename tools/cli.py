from typing import Any, Dict, Union

import click


def _recurse_cli(
    cli_element: Union[click.Command, click.Group, click.CommandCollection],
    ctx: click.Context,
    io_dict: Dict[str, Any],
    get_help: bool = False,
) -> None:
    """
    Recursive function that checks the type of the command (key) and decides:
    1. In case of `click.Group` or `click.CommandCollection` (aggregate commands),
        the function collects the name and recurses one layer deeper
        for each sub-command.
    2. In case of `click.Command`, the terminus command has been reached. The function
        collects the name, parameters and args, flattens them and saves them as
        dictionary keys.
    Args:
        cli_element: CLI Collection as input for recursion, typically `KedroCLI`.
        ctx: Click Context, created by the wrapper function.
        io_dict: Input-output dictionary, mutated during the recursion.
        get_help: Boolean fork - allows either:
            raw structure - nested dictionary until final value of `None`
            help structure - nested dictionary where leaves are `--help` cmd output

    Returns:
        None (underlying `io_dict` is mutated by the recursion)
    """
    if isinstance(cli_element, (click.Group, click.CommandCollection)):
        element_name = cli_element.name or "kedro"
        io_dict[element_name] = {}
        for command_name in cli_element.list_commands(ctx):
            _recurse_cli(
                cli_element.get_command(ctx, command_name),  # type: ignore
                ctx,
                io_dict[element_name],
                get_help,
            )

    elif isinstance(cli_element, click.Command):
        if get_help:  # gets formatted CLI help incl params for printing
            io_dict[cli_element.name] = cli_element.get_help(ctx)
        else:  # gets params for structure purposes
            nested_parameter_list = [option.opts for option in cli_element.get_params(ctx)]
            io_dict[cli_element.name] = dict.fromkeys(
                [item for sublist in nested_parameter_list for item in sublist], None
            )


def get_cli_structure(
    cli_obj: Union[click.Command, click.Group, click.CommandCollection],
    get_help: bool = False,
) -> Dict[str, Any]:
    """Convenience wrapper function for `_recurse_cli` to work within
    `click.Context` and return a `dict`.
    """
    output: Dict[str, Any] = dict()
    with click.Context(cli_obj) as ctx:  # type: ignore
        _recurse_cli(cli_obj, ctx, output, get_help)
    return output
