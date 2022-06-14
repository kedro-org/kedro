"""Dummy plugin with simple hook implementations."""
import logging

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
        name="test_plugin_starter",
        template_path="https://github.com/kedro-org/kedro-starters/",
        directory="pandas-iris",
    )
]

hooks = MyPluginHook()
