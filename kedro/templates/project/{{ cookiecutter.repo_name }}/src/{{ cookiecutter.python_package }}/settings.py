"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://kedro.readthedocs.io/en/stable/kedro_project_setup/settings.html."""

# Instantiated project hooks.
# HOOKS = (,)

# Installed plugins for which to disable hook auto-registration.
# DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Class that manages storing KedroSession data.
# from kedro_viz.integrations.kedro.sqlite_store import SQLiteStore
# from pathlib import Path
# SESSION_STORE_CLASS = SQLiteStore
# Keyword arguments to pass to the `SESSION_STORE_CLASS` constructor.
# SESSION_STORE_ARGS = {
#     "path": "./sessions"
# }


# Directory that holds configuration.
# CONF_SOURCE = "conf"

# Class that manages how configuration is loaded.
# from kedro.config import OmegaConfigLoader
# CONFIG_LOADER_CLASS = OmegaConfigLoader
# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
# CONFIG_LOADER_ARGS = {
#       "config_patterns": {
#           "spark" : ["spark*/"],
#           "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
#       }
# }

# Class that manages Kedro's library components.
# from kedro.framework.context import KedroContext
# CONTEXT_CLASS = KedroContext

# Class that manages the Data Catalog.
# from kedro.io import DataCatalog
# DATA_CATALOG_CLASS = DataCatalog
