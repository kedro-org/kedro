"""Dummy plugin with simple hook implementations."""
import logging

from kedro.framework.hooks import hook_impl

from kedro.framework.cli.starters import _STARTERS_REPO

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MyPluginHook:
    @hook_impl
    def after_catalog_created(
        self, catalog
    ):  # pylint: disable=unused-argument,no-self-use
        logger.info("Reached after_catalog_created hook")


hooks = MyPluginHook()
