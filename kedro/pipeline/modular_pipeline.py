"""Helper to integrate modular pipelines into a master pipeline."""
import copy
from typing import AbstractSet, Dict, List, Set, Union

from kedro.pipeline.node import Node
from kedro.pipeline.pipeline import (
    TRANSCODING_SEPARATOR,
    Pipeline,
    _strip_transcoding,
    _transcode_split,
)

_PARAMETER_KEYWORDS = ("params:", "parameters")


class ModularPipelineError(Exception):
    """Raised when a modular pipeline is not adapted and integrated
    appropriately using the helper.
    """

    pass


def _is_parameter(name: str) -> bool:
    return any(name.startswith(param) for param in _PARAMETER_KEYWORDS)


def _validate_inputs_outputs(
    inputs: AbstractSet[str], outputs: AbstractSet[str], pipe: Pipeline
) -> None:
    """Safeguards to ensure that:
    - parameters are not specified under inputs
    - inputs are only free inputs
    - outputs do not contain free inputs
    """
    inputs = {_strip_transcoding(k) for k in inputs}
    outputs = {_strip_transcoding(k) for k in outputs}

    if any(_is_parameter(i) for i in inputs):
        raise ModularPipelineError(
            "Parameters should be specified in the `parameters` argument"
        )

    free_inputs = {_strip_transcoding(i) for i in pipe.inputs()}

    if not inputs <= free_inputs:
        raise ModularPipelineError("Inputs should be free inputs to the pipeline")

    if outputs & free_inputs:
        raise ModularPipelineError("Outputs can't contain free inputs to the pipeline")


def _validate_datasets_exist(
    inputs: AbstractSet[str],
    outputs: AbstractSet[str],
    parameters: AbstractSet[str],
    pipe: Pipeline,
) -> None:
    inputs = {_strip_transcoding(k) for k in inputs}
    outputs = {_strip_transcoding(k) for k in outputs}

    existing = {_strip_transcoding(ds) for ds in pipe.data_sets()}
    non_existent = (inputs | outputs | parameters) - existing
    if non_existent:
        raise ModularPipelineError(
            f"Failed to map datasets and/or parameters: "
            f"{', '.join(sorted(non_existent))}"
        )


def pipeline(
    pipe: Pipeline,
    *,
    inputs: Union[str, Set[str], Dict[str, str]] = None,
    outputs: Union[str, Set[str], Dict[str, str]] = None,
    parameters: Dict[str, str] = None,
    namespace: str = None,
) -> Pipeline:
    """Create a copy of the pipeline and its nodes,
    with some dataset names and node names modified.

    Args:
        pipe: Original modular pipeline to integrate
        inputs: A name or collection of input names to be exposed as connection points
            to other pipelines upstream.
            When str or Set[str] is provided, the listed input names will stay
            the same as they are named in the provided pipeline.
            When Dict[str, str] is provided, current input names will be
            mapped to new names.
            Must only refer to the pipeline's free inputs.
        outputs: A name or collection of names to be exposed as connection points
            to other pipelines downstream.
            When str or Set[str] is provided, the listed output names will stay
            the same as they are named in the provided pipeline.
            When Dict[str, str] is provided, current output names will be
            mapped to new names.
            Can refer to both the pipeline's free outputs, as well as
            intermediate results that need to be exposed.
        parameters: A map of existing parameter to the new one.
        namespace: A prefix to give to all dataset names,
            except those explicitly named with the `inputs`/`outputs`
            arguments, and parameter references (`params:` and `parameters`).

    Raises:
        ModularPipelineError: When inputs, outputs or parameters are incorrectly
            specified, or they do not exist on the original pipeline.
        ValueError: When underlying pipeline nodes inputs/outputs are not
            any of the expected types (str, dict, list, or None).

    Returns:
        A new ``Pipeline`` object with the new nodes, modified as requested.
    """
    # pylint: disable=protected-access
    inputs = _to_dict(inputs)
    outputs = _to_dict(outputs)
    parameters = _to_dict(parameters)

    _validate_datasets_exist(inputs.keys(), outputs.keys(), parameters.keys(), pipe)
    _validate_inputs_outputs(inputs.keys(), outputs.keys(), pipe)

    mapping = {**inputs, **outputs, **parameters}

    def _prefix(name: str) -> str:
        return f"{namespace}.{name}" if namespace else name

    def _is_transcode_base_in_mapping(name: str) -> bool:
        base_name, _ = _transcode_split(name)
        return base_name in mapping

    def _map_transcode_base(name: str):
        base_name, transcode_suffix = _transcode_split(name)
        return TRANSCODING_SEPARATOR.join((mapping[base_name], transcode_suffix))

    def _rename(name: str):
        rules = [
            # if name mapped to new name, update with new name
            (lambda n: n in mapping, lambda n: mapping[n]),
            # if it's a parameter, leave as is (don't namespace)
            (_is_parameter, lambda n: n),
            # if transcode base is mapped to a new name, update with new base
            (_is_transcode_base_in_mapping, _map_transcode_base),
            # if namespace given, prefix name using that namespace
            (lambda n: bool(namespace), _prefix),
        ]

        for predicate, processor in rules:
            if predicate(name):
                return processor(name)

        # leave name as is
        return name

    def _process_dataset_names(
        datasets: Union[None, str, List[str], Dict[str, str]]
    ) -> Union[None, str, List[str], Dict[str, str]]:
        if datasets is None:
            return None
        if isinstance(datasets, str):
            return _rename(datasets)
        if isinstance(datasets, list):
            return [_rename(name) for name in datasets]
        if isinstance(datasets, dict):
            return {key: _rename(value) for key, value in datasets.items()}

        raise ValueError(  # pragma: no cover
            f"Unexpected input {datasets} of type {type(datasets)}"
        )

    def _copy_node(node: Node) -> Node:
        new_namespace = node.namespace
        if namespace:
            new_namespace = (
                f"{namespace}.{node.namespace}" if node.namespace else namespace
            )

        return node._copy(
            inputs=_process_dataset_names(node._inputs),
            outputs=_process_dataset_names(node._outputs),
            namespace=new_namespace,
        )

    new_nodes = [_copy_node(n) for n in pipe.nodes]

    return Pipeline(new_nodes)


def _to_dict(element: Union[None, str, Set[str], Dict[str, str]]) -> Dict[str, str]:
    if element is None:
        return {}
    if isinstance(element, str):
        return {element: element}
    if isinstance(element, dict):
        return copy.deepcopy(element)
    return {item: item for item in element}
