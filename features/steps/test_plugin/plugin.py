"""Dummy plugin with simple hook implementations."""
import logging

from kedro.framework.hooks import hook_impl


class MyPluginHook:
    @hook_impl
    def after_catalog_created(
        self, catalog
    ):  # pylint: disable=unused-argument,no-self-use
        logging.info("Reached after_catalog_created hook")


hooks = MyPluginHook()
