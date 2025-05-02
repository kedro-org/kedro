"""``kedro.framework.cli`` implements commands available from Kedro's CLI."""

# The constant need to be defined first otherwise it causes circular dependencies
ORANGE = (255, 175, 0)
BRIGHT_BLACK = (128, 128, 128)

from .cli import main  # noqa: E402
from .utils import command_with_verbosity, load_entry_points  # noqa: E402

__all__ = ["main", "command_with_verbosity", "load_entry_points"]
