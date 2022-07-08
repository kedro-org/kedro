"""Dummy plugin with simple hook implementations."""
import logging
from pathlib import Path

from kedro.framework.cli.starters import KedroStarterSpec
from kedro.framework.hooks import hook_impl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MyPluginHook:
    @hook_impl
    def after_catalog_created(
        self, catalog
    ):  # pylint: disable=unused-argument, no-self-use
        logger.info("Reached after_catalog_created hook")


starters = [
    KedroStarterSpec(
        "test_plugin_starter",
        template_path=str((Path(__file__).parents[1] / "test_starter").resolve()),
    )
]

hooks = MyPluginHook()
