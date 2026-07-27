import sys
import textwrap
import threading
import time

import pytest

from kedro.framework.project import _ProjectPipelines, configure_project, pipelines
from kedro.pipeline import Pipeline


@pytest.fixture
def mock_package_name_with_pipelines_file(tmpdir):
    pipelines_file_path = tmpdir.mkdir("test_package") / "pipeline_registry.py"
    pipelines_file_path.write(
        textwrap.dedent(
            """
                from kedro.pipeline import Pipeline
                def register_pipelines():
                    return {"new_pipeline": Pipeline([])}
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition("test_package")
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_pipelines_without_configure_project_is_empty(
    mock_package_name_with_pipelines_file,
):
    # Reimport `pipelines` from `kedro.framework.project` to ensure that
    # it was not set by a prior call to the `configure_project` function.
    del sys.modules["kedro.framework.project"]
    from kedro.framework.project import pipelines

    assert pipelines == {}


@pytest.fixture
def mock_package_name_with_unimportable_pipelines_file(tmpdir):
    pipelines_file_path = tmpdir.mkdir("test_broken_package") / "pipeline_registry.py"
    pipelines_file_path.write(
        textwrap.dedent(
            """
                import this_is_not_a_real_thing
                from kedro.pipeline import Pipeline
                def register_pipelines():
                    return {"new_pipeline": Pipeline([])}
            """
        )
    )
    project_path, package_name, _ = str(pipelines_file_path).rpartition(
        "test_broken_package"
    )
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_pipelines_after_configuring_project_shows_updated_values(
    mock_package_name_with_pipelines_file,
):
    configure_project(mock_package_name_with_pipelines_file)
    assert isinstance(pipelines["new_pipeline"], Pipeline)


def test_configure_project_should_not_raise_for_unimportable_pipelines(
    mock_package_name_with_unimportable_pipelines_file,
):
    # configure_project should not raise error for unimportable pipelines
    # since pipelines loading is lazy
    configure_project(mock_package_name_with_unimportable_pipelines_file)

    # accessing data should raise for unimportable pipelines
    with pytest.raises(
        ModuleNotFoundError, match="No module named 'this_is_not_a_real_thing'"
    ):
        _ = pipelines["new_pipeline"]


# --- Thread-safety tests ---


def _make_pipelines_with_mock_loader(call_counter=None, sleep=0.0):
    """Return a _ProjectPipelines whose loader records call count."""
    counter = call_counter if call_counter is not None else []

    def register_pipelines():
        counter.append(1)
        if sleep:
            time.sleep(sleep)
        return {"pipe_a": Pipeline([]), "pipe_b": Pipeline([])}

    p = _ProjectPipelines()
    p._pipelines_module = "fake_module"
    p._get_pipelines_registry_callable = lambda _: register_pipelines
    return p, counter


def test_load_data_fires_exactly_once_under_concurrent_first_load():
    """register_pipelines() must be invoked exactly once even when many threads
    race through the unloaded state at the same time."""
    n_threads = 20
    barrier = threading.Barrier(n_threads)
    errors = []
    p, counter = _make_pipelines_with_mock_loader(sleep=0.02)

    def reader():
        try:
            barrier.wait(timeout=5)
            _ = p["pipe_a"]
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert all(
        not t.is_alive() for t in threads
    ), "threads did not finish — possible deadlock"
    assert not errors, errors
    assert len(counter) == 1


def test_set_requested_concurrent_with_reads_does_not_raise():
    """Concurrent set_requested() and dict reads must not crash or return
    torn state — the wrapper snapshot must remain usable for the full call."""
    n_reader_threads = 10
    n_iterations = 100
    errors = []
    p, _ = _make_pipelines_with_mock_loader()

    def reader():
        try:
            for _ in range(n_iterations):
                _ = len(p)
        except Exception as e:
            errors.append(e)

    def invalidator():
        for _ in range(n_iterations):
            p.set_requested(None)
            p.set_requested(["pipe_a"])

    threads = [threading.Thread(target=reader) for _ in range(n_reader_threads)]
    threads += [threading.Thread(target=invalidator) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert all(
        not t.is_alive() for t in threads
    ), "threads did not finish — possible deadlock"
    assert not errors, errors


def test_configure_concurrent_with_reads_does_not_raise():
    """configure() resetting all state while readers are active must not
    produce crashes or inconsistent internal state."""
    n_reader_threads = 10
    n_iterations = 100
    errors = []
    p, _ = _make_pipelines_with_mock_loader()

    def reader():
        try:
            for _ in range(n_iterations):
                _ = len(p)
        except Exception as e:
            errors.append(e)

    def reconfigurer():
        for _ in range(n_iterations):
            p.configure("fake_module")

    threads = [threading.Thread(target=reader) for _ in range(n_reader_threads)]
    threads += [threading.Thread(target=reconfigurer)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert all(
        not t.is_alive() for t in threads
    ), "threads did not finish — possible deadlock"
    assert not errors, errors
