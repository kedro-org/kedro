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


def test_first_load_runs_once():
    """register_pipelines() fires exactly once even with many concurrent first reads."""
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

    threads = [threading.Thread(target=reader, daemon=True) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert all(
        not t.is_alive() for t in threads
    ), "threads did not finish — possible deadlock"
    assert not errors, errors
    assert len(counter) == 1


def test_concurrent_set_requested_and_reads():
    """Smoke test: concurrent set_requested() and reads must not crash or hang."""
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
        try:
            for _ in range(n_iterations):
                p.set_requested(None)
                p.set_requested(["pipe_a"])
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=reader, daemon=True) for _ in range(n_reader_threads)
    ]
    threads += [threading.Thread(target=invalidator, daemon=True) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert all(
        not t.is_alive() for t in threads
    ), "threads did not finish — possible deadlock"
    assert not errors, errors


@pytest.mark.parametrize(
    "invalidate",
    [
        lambda p: p.set_requested(["pipe_a"]),
        lambda p: p.configure("fake_module"),
    ],
    ids=["set_requested", "configure"],
)
def test_invalidation_race_no_stale_read(invalidate):
    """A concurrent invalidation right as _load_data() returns must not affect
    the read that's already in flight — it must see the pre-invalidation content.

    Real threads can't reliably land in this window (it's a couple of
    bytecodes wide), so the interleaving is forced deterministically instead.
    """
    p, _ = _make_pipelines_with_mock_loader()
    _ = p["pipe_a"]  # warm the cache: 2 pipelines loaded

    original_load_data = p._load_data

    def racing_load_data():
        result = original_load_data()
        invalidate(p)  # simulate a concurrent set_requested()/configure()
        return result

    p._load_data = racing_load_data

    assert len(p) == 2


def test_concurrent_configure_and_reads():
    """Smoke test: concurrent configure() and reads must not crash or hang."""
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
        try:
            for _ in range(n_iterations):
                p.configure("fake_module")
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=reader, daemon=True) for _ in range(n_reader_threads)
    ]
    threads += [threading.Thread(target=reconfigurer, daemon=True)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert all(
        not t.is_alive() for t in threads
    ), "threads did not finish — possible deadlock"
    assert not errors, errors
