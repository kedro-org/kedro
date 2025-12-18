"""MkDocs hooks for custom Jinja2 filters."""

import os

# Versions to track with production Heap analytics
PRODUCTION_VERSIONS = {"stable", "1.1.1", "1.1.0", "1.0.0"}


def env_override(default_appid):
    """Return the appropriate Heap App ID based on the Read the Docs environment.

    Args:
        default_appid: The default App ID (Development environment)

    Returns:
        The Heap App ID for the current environment
    """
    build_version = os.getenv("READTHEDOCS_VERSION")

    # QA environment for unreleased docs (main branch)
    if build_version == "latest":
        return os.environ.get("HEAP_APPID_QA", default_appid)

    # Production environment for stable and specific version tags
    if build_version in PRODUCTION_VERSIONS:
        return os.environ.get("HEAP_APPID_PROD", default_appid)

    # Development environment for PR builds, local builds, etc.
    return default_appid


def on_env(env, config, files):
    """Add custom Jinja2 filters to the environment."""
    env.filters["env_override"] = env_override
    return env
