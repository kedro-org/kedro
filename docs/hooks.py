"""MkDocs hooks for custom Jinja2 filters."""

import os


def env_override(default_appid):
    """Return the appropriate Heap App ID based on the Read the Docs environment.
    
    Args:
        default_appid: The default App ID (Development environment)
        
    Returns:
        The Heap App ID for the current environment
    """
    build_version = os.getenv("READTHEDOCS_VERSION")

    if build_version == "latest":
        return os.environ.get("HEAP_APPID_QA", default_appid)
    if build_version == "stable":
        return os.environ.get("HEAP_APPID_PROD", default_appid)

    return default_appid  # default to Development for local builds


def on_env(env, config, files):
    """Add custom Jinja2 filters to the environment."""
    env.filters["env_override"] = env_override
    return env

