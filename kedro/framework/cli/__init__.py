"""``kedro.framework.cli`` implements commands available from Kedro's CLI.
"""

from .cli import main
from .utils import command_with_verbosity, load_entry_points

__all__ = ["main", "command_with_verbosity", "load_entry_points"]

ORANGE = (255, 175, 0)
BRIGHT_BLACK = (128, 128, 128)
