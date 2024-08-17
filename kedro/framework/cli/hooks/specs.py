"""A module containing specifications for all callable hooks in the Kedro CLI's execution timeline.
For more information about these specifications, please visit
[Pluggy's documentation](https://pluggy.readthedocs.io/en/stable/#specs)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .markers import cli_hook_spec

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata


class CLICommandSpecs:
    """Namespace that defines all specifications for Kedro CLI's lifecycle hooks."""

    @cli_hook_spec
    def before_command_run(
        self,
        project_metadata: ProjectMetadata,
        command_args: list[str],
    ) -> None:
        """Hooks to be invoked before a CLI command runs.
        It receives the ``project_metadata`` as well as
        all command line arguments that were used, including the command
        and subcommand themselves.

        Args:
            project_metadata: The Kedro project's metadata.
            command_args: The command line arguments that were used.
        """
        pass

    @cli_hook_spec
    def after_command_run(
        self, project_metadata: ProjectMetadata, command_args: list[str], exit_code: int
    ) -> None:
        """Hooks to be invoked after a CLI command runs.
        It receives the ``project_metadata`` as well as
        all command line arguments that were used, including the command
        and subcommand themselves and if the operation was successful or not.

        Args:
            project_metadata: The Kedro project's metadata.
            command_args: The command line arguments that were used.
            exit_code: Exit code raised by Click application after completion
        """
        pass
