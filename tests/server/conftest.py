from pathlib import Path

import pytest

from kedro.server.http_server import create_http_server


@pytest.fixture(autouse=True)
def _patch_seed_bootstrap_cache(mocker):
    """Prevent _seed_bootstrap_cache from mutating the inspection module's cache during server tests."""
    mocker.patch("kedro.server.http_server._seed_bootstrap_cache")


@pytest.fixture
def make_http_server(mocker, tmp_path):
    """Factory fixture that creates a bootstrapped HTTP server app for testing.

    Patches ``_resolve_project_path`` and ``bootstrap_project`` so callers don't
    have to repeat that boilerplate. The ``tmp_path`` used internally is the same
    instance pytest injects into the test, so assertions on ``project_path`` work
    when the test also declares ``tmp_path``.

    Usage::

        def test_something(make_http_server):
            app = make_http_server()  # default env
            app = make_http_server(env="staging")
    """

    def _factory(*, env=None, conf_source=None):
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        return create_http_server(
            project_path=str(project_path), env=env, conf_source=conf_source
        )

    return _factory
