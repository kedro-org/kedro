"""Project settings."""
from {{cookiecutter.python_package}}.hooks import ProjectHooks

# Instantiate and list your project hooks here
HOOKS = (ProjectHooks(),)

# List the installed plugins for which to disable auto-registry
# DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Define where to store data from a KedroSession. Defaults to BaseSessionStore.
# from kedro.framework.session.store import ShelveStore
# SESSION_STORE_CLASS = ShelveStore

# Define keyword arguments to be passed to `SESSION_STORE_CLASS` constructor
# SESSION_STORE_ARGS = {
#     "path": "./sessions"
# }

# Define custom context class. Defaults to `KedroContext`
# CONTEXT_CLASS = KedroContext

# Define the configuration folder. Defaults to `conf`
# CONF_SOURCE = "conf"

# Select the project ConfigLoader class here.
# Defaults to kedro.config.ConfigLoader
# Define the config loader. Defaults to ConfigLoader.
# from kedro.config import TemplatedConfigLoader
# CONFIG_LOADER_CLASS = TemplatedConfigLoader

# Define keyword arguments to be passed to `CONFIG_LOADER_CLASS` constructor.
# These kwargs depend on the `ConfigLoader` class implementation.
# CONFIG_LOADER_ARGS = {
#     "globals_pattern": "*globals.yml",
#     "base_env": "base",
#     "default_run_env": "local",
# }
