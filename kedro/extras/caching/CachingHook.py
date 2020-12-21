"""Tooling to store the state of previous pipeline runs """
import abc
import inspect
import json
import logging
import pickle
from hashlib import md5
from pathlib import Path
from typing import Any, Dict, List, Callable, Union

from kedro.framework.hooks.markers import hook_impl
from kedro.io import MemoryDataSet
from kedro.io.data_catalog import DataCatalog, _FrozenDatasets
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node

STATE_PATH = Path("pipeline.kstate")


class AbstractCachingHook(abc.ABC):
    @abc.abstractmethod
    def _load(self) -> Any:
        raise NotImplementedError(
            "`{}` is a subclass of AbstractCachingHook and"
            "it must implement the `_load` method".format(self.__class__.__name__)
        )

    def _persist(self) -> Any:
        raise NotImplementedError(
            "`{}` is a subclass of AbstractCachingHook and"
            "it must implement the `_persist` method".format(self.__class__.__name__)
        )


class LocalFileCachingHook(AbstractCachingHook):

    def __init__(self, path: Union[Path, str]):
        self._location = path or STATE_PATH
        self._node_state: Dict[str, str] = {}
        self._dataset_state: Dict[str, int] = {}
        self._counter = 1
        self._load()

    def _load(self) -> None:
        """loads state from disk to memory"""
        try:
            with open(self._location) as f:
                data = json.load(f)
                self._node_state = data.get("nodes", {})
                self._dataset_state = data.get("datasets", {})
                self._counter = data.get("counter", 1)
        except FileNotFoundError:
            pass

    def _persist(self) -> None:
        """persists the state of memory to disk"""
        # may also support other state locations such as dynamoDB tables or remote state (take inspiration from
        # terraform for this)
        logging.warning("Persisting call counts")
        with open(self._location, "w") as f:
            data = {
                "nodes": self._node_state,
                "datasets": self._dataset_state,
                "counter": self._counter
            }
            json.dump(data, f, indent=4)

    @hook_impl
    def after_pipeline_run(self,
                           run_params: Dict[str, Any],
                           run_result: Dict[str, Any],
                           pipeline: Pipeline,
                           catalog: DataCatalog,
                           ):
        self._persist()

    @hook_impl
    def before_node_run(
            self,
            node: Node,
            catalog: DataCatalog,
            inputs: Dict[str, Any],
            is_async: bool,
            run_id: str,
    ) -> bool:
        # determine code has changed
        if self.has_code_changed(node):
            return False

        inputs, outputs = get_inputs_outputs(catalog, inputs, node)
        if _check_memory_datasets(inputs, outputs, catalog.datasets):
            return False

        if self._check_inputs_outputs_age(outputs, inputs):
            return False

        # ... determine all the other crap
        # OK let's overwrite. No outputs written and no execution
        logging.warning("Determined to skip node %s", node.name)
        node._outputs = {}

        # replace node function body with empty call
        def mock(*args, **kwargs):
            return {}

        mock.__signature__ = inspect.signature(node._func)
        node._func = mock
        return True

    def has_code_changed(self, node: Node):
        fingerprint = get_function_fingerprint(node._func)
        previous = self._node_state.get(node.name, "")
        return fingerprint != previous

    def _check_inputs_outputs_age(self, outputs: List[str], inputs: List[str]):
        """Checks that the latest input is older than the oldest output."""
        input_counters = [self._dataset_state.get(in_) for in_ in inputs]
        output_counters = [self._dataset_state.get(out) for out in outputs]

        latest_input = sorted(input_counters)[-1] if len(input_counters) > 0 else 0
        oldest_output = sorted(output_counters)[0] if len(output_counters) > 0 else latest_input+1

        return latest_input >= oldest_output

    @hook_impl
    def after_node_run(  # pylint: disable=too-many-arguments
            self,
            node: Node,
            catalog: DataCatalog,
            inputs: Dict[str, Any],
            outputs: Dict[str, Any],
            is_async: bool,
            run_id: str,
    ) -> None:
        """Stores the results of this node run to be able to skip it in the future if needed.
        
        To enable skipping, we remember: 
         - the node's bytecode (by remembering a hash of it)
         - the datetime of completion of the node -> all outputs are remembered with this timestamp
        """
        # remember code
        fingerprint = get_function_fingerprint(node._func)
        self._node_state[node.name] = fingerprint

        # remember outputs
        for output in outputs.keys():
            self._dataset_state[output] = self._counter
            self._counter += 1

    @hook_impl
    def on_node_error(
            self,
            error: Exception,
            node: Node,
            catalog: DataCatalog,
            inputs: Dict[str, Any],
            is_async: bool,
            run_id: str,
    ):
        """Reset node to make sure it's run again when this happens"""
        pass


def get_inputs_outputs(catalog: DataCatalog, inputs, node: Node):
    # outputs = [_sub_nonword_chars(output) for output in node.outputs]
    outputs = node.outputs
    # outputs = [getattr(catalog.datasets, output) for output in :qa
    inputs: List[str] = [
        input_ for input_ in node.inputs
        if input_ != "parameters" and not input_.startswith("params:")
    ]
    return inputs, outputs


def get_function_fingerprint(func: Any, ignore_keys: List = None):
    """A function that helps us determine if a node has changed.

    This function takes a function as an argument and returns a fingerprint for it.
    This fingerprint is expected to change whenever the functions code changes.

    To read more about this, check
    https://docs.python.org/3.8/reference/datamodel.html
    and
    https://stackoverflow.com/questions/64534943/determine-if-a-python-function-has-changed
    or
    https://stackoverflow.com/questions/18134087/how-do-i-check-if-a-python-function-changed-in-live-code
    """
    ignore_keys = ignore_keys or []
    code_obj = func.__code__
    to_hash = {
        "co_code": code_obj.co_code,
        "co_consts": code_obj.co_consts,
        "co_argcount": code_obj.co_argcount,
        "co_kwonlyargcount": code_obj.co_kwonlyargcount,
        "co_name": code_obj.co_name,
        "co_names": code_obj.co_names,
        "co_stacksize": code_obj.co_stacksize,
        "co_varnames": code_obj.co_varnames,
    }
    for key in ignore_keys:
        del to_hash[key]
    # create
    bytes_ = pickle.dumps(to_hash)
    _hash = md5(bytes_).hexdigest()
    logging.info(f"function hash for function {func.__code__.co_name} is {_hash}")
    return _hash


def _check_memory_datasets(inputs, outputs, datasets: _FrozenDatasets):
    def _get(name, ):
        return datasets.__getattribute__(name)

    return any(isinstance(_get(output), MemoryDataSet) for output in outputs) or any(
        isinstance(_get(input_), MemoryDataSet) for input_ in inputs)
