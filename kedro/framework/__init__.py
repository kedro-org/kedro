"""``kedro.framework`` provides Kedro's framework components """
from typing import Optional

from attr import define, field


@define(order=True)
class KedroStarterSpec:  # pylint: disable=too-few-public-methods
    """Specification of custom kedro starter template
    Args:
        alias: alias of the starter which shows up on `kedro starter list` and is used
        by the starter argument of `kedro new`
        template_path: path to a directory or a URL to a remote VCS repository supported
        by `cookiecutter`
        directory: optional directory inside the repository where the starter resides.
        origin: reserved field used by kedro internally to determine where the starter
        comes from, users do not need to provide this field.
    """

    alias: str
    template_path: str
    directory: Optional[str] = None
    origin: Optional[str] = field(init=False)
