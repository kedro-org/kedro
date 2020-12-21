import json
import math
from pathlib import Path
from random import random
from shutil import rmtree
from tempfile import TemporaryFile, gettempdir
from unittest.mock import MagicMock, Mock

from kedro.extras.caching.CachingHook import LocalFileCachingHook, get_function_fingerprint, get_inputs_outputs
import pytest
import os

from kedro.extras.datasets.json import JSONDataSet
from kedro.framework.hooks import get_hook_manager
from kedro.framework.session import KedroSession
from kedro.io import DataCatalog, MemoryDataSet
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner

STATIC_STRING = "ABC"


# some functions to use for equality evaluations
def ident(x):
    return x


def a_loop():
    for i in range(10):
        a = "1"


def with_imported():
    os.listdir()


def a_func():
    # with comment
    a_loop()
    a = 2
    ident(STATIC_STRING)
    with_imported()
    return {"a": a}


def b_func(a_out):
    # with comment
    a_loop()
    b = 2
    ident(STATIC_STRING)
    with_imported()
    return {"b": b}


def _run_pipeline_twice(pipeline: Pipeline, catalog: DataCatalog):
    manager = get_hook_manager()
    runner = SequentialRunner()
    tmp_dir = gettempdir()
    state_path = Path(tmp_dir) / "state.kstate"
    state_path.unlink(missing_ok=True)  # ensure no old file in use

    # run pipeline 1st time
    hook1 = LocalFileCachingHook(state_path)
    manager.register(hook1)
    runner.run(pipeline, catalog, "1")
    manager.unregister(hook1)
    hook1._persist()

    # run pipeline 2nd time
    hook2 = LocalFileCachingHook(state_path)
    manager.register(hook2)
    runner.run(pipeline, catalog, "2")
    manager.unregister(hook2)
    hook2._persist()
    with open(state_path) as f:
        state = f.read()
    return hook1, hook2, state


def test_simple_in_memory_pipeline():
    # Assemble nodes into a pipeline
    a = Mock()
    b = Mock()
    pipeline = Pipeline([node(lambda: a(), inputs=None, outputs="a_out", name="A"), node(lambda a: b(), inputs="a_out",
                                                                               outputs="b_out", name="B")])
    data_catalog = DataCatalog({"a_out": MemoryDataSet(), "b_out": MemoryDataSet()})
    hook1, hook2, state_content = _run_pipeline_twice(pipeline, data_catalog)

    # both nodes can't be skipped due to MemoryDataSet exclusion criteria
    assert a.call_count == 2
    assert b.call_count == 2

    # check state_content
    state = json.loads(state_content)
    assert state['datasets']['a_out'] == 3
    assert state['datasets']['b_out'] == 4


def test_simple_pipeline(tmp_path):
    # Assemble nodes into a pipeline
    a_called = Mock()
    def a():
        a_called()
        return {"a": 1}
    b_called = Mock()
    def b(a_out):
        b_called()
        return {"b": 1}

    pipeline = Pipeline([node(a, inputs=None, outputs="a_out", name="A"), node(b, inputs="a_out", outputs="b_out",
                                                                                name="B")])
    data_catalog = DataCatalog({"a_out": JSONDataSet(str(tmp_path / "a.json")), "b_out": JSONDataSet(str(tmp_path / "b.json"))})
    hook1, hook2, state_content = _run_pipeline_twice(pipeline, data_catalog)

    assert a_called.call_count == 1
    assert b_called.call_count == 1
    # check state_content
    state = json.loads(state_content)
    assert state['datasets']['a_out'] == 1
    assert state['datasets']['b_out'] == 2


def test_expect_two_functions_equal():
    # ignoring name in specific case because the function's can't have the same name in the same namespace
    b = a_func
    hash_one = get_function_fingerprint(a_func, ["co_name"])
    hash_two = get_function_fingerprint(b, ["co_name"])
    assert hash_one == hash_two

    # works for lambdas
    hash_one = get_function_fingerprint(lambda: print(1))
    hash_two = get_function_fingerprint(lambda: print(2))
    assert hash_one != hash_two

    hash_one = get_function_fingerprint(lambda: print(1))
    hash_two = get_function_fingerprint(lambda: print(1))
    assert hash_one == hash_two

    # works for randomness
    hash_one = get_function_fingerprint(lambda: random())
    hash_two = get_function_fingerprint(lambda: random())
    assert hash_one == hash_two

# def test_get_inputs_outputs():
#     # TODO test
#     # get_inputs_outputs()
#     pass
#
#
# def test_after_node_run(caching_hook: LocalFileCachingHook):
#     # TODO test
#     caching_hook.after_node_run()
#     pass
#
#
# def test_before_node_run(caching_hook: LocalFileCachingHook):
#     # TODO test
#     caching_hook.before_node_run()
#     pass