"""Dummy plugin with simple hook implementations."""
import logging

from kedro.framework.hooks import hook_impl
from kedro.pipeline import Pipeline, node


class MyPluginHook:
    @hook_impl
    def after_catalog_created(
        self, catalog
    ):  # pylint: disable=unused-argument,no-self-use
        logging.info("Reached after_catalog_created hook")

    @hook_impl
    def register_pipelines(self):  # pylint: disable=no-self-use
        return {
            "from_plugin": pipeline([node(lambda: "sth", inputs=None, outputs="x")])
        }


hooks = MyPluginHook()
