"""Helper to integrate modular pipelines into a master pipeline."""
from __future__ import annotations

import copy
from typing import AbstractSet, Iterable

from kedro.pipeline.node import Node
from kedro.pipeline.pipeline import (
    TRANSCODING_SEPARATOR,
    Pipeline,
    _strip_transcoding,
    _transcode_split,
)


class ModularPipelineError(Exception):
    """Raised when a modular pipeline is not adapted and integrated
    appropriately using the helper.
    """

    pass


def _is_all_parameters(name: str) -> bool:
    return name == "parameters"


def _is_single_parameter(name: str) -> bool:
    return name.startswith("params:")


def _is_parameter(name: str) -> bool:
    return _is_single_parameter(name) or _is_all_parameters(name)


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
            "Parameters should be specified in the 'parameters' argument"
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

    existing = {_strip_transcoding(ds) for ds in pipe.datasets()}
    non_existent = (inputs | outputs | parameters) - existing
    if non_existent:
        raise ModularPipelineError(
            f"Failed to map datasets and/or parameters: "
            f"{', '.join(sorted(non_existent))}"
        )


def _get_dataset_names_mapping(
    names: str | set[str] | dict[str, str] | None = None
) -> dict[str, str]:
    """Take a name or a collection of dataset names
    and turn it into a mapping from the old dataset names to the provided ones if necessary.

    Args:
        names: A dataset name or collection of dataset names.
            When str or set[str] is provided, the listed names will stay
            the same as they are named in the provided pipeline.
            When dict[str, str] is provided, current names will be
            mapped to new names in the resultant pipeline.
    Returns:
        A dictionary that maps the old dataset names to the provided ones.
    Examples:
        >>> _get_dataset_names_mapping("dataset_name")
        {"dataset_name": "dataset_name"}  # a str name will stay the same
        >>> _get_dataset_names_mapping(set(["ds_1", "ds_2"]))
        {"ds_1": "ds_1", "ds_2": "ds_2"}  # a set[str] of names will stay the same
        >>> _get_dataset_names_mapping({"ds_1": "new_ds_1_name"})
        {"ds_1": "new_ds_1_name"}  # a dict[str, str] of names will map key to value
    """
    if names is None:
        return {}
    if isinstance(names, str):
        return {names: names}
    if isinstance(names, dict):
        return copy.deepcopy(names)

    return {item: item for item in names}


def _normalize_param_name(name: str) -> str:
    """Make sure that a param name has a `params:` prefix before passing to the node"""
    return name if name.startswith("params:") else f"params:{name}"


def _get_param_names_mapping(
    names: str | set[str] | dict[str, str] | None = None
) -> dict[str, str]:
    """Take a parameter or a collection of parameter names
    and turn it into a mapping from existing parameter names to new ones if necessary.
    It follows the same rule as `_get_dataset_names_mapping` and
    prefixes the keys on the resultant dictionary with `params:` to comply with node's syntax.

    Args:
        names: A parameter name or collection of parameter names.
            When str or set[str] is provided, the listed names will stay
            the same as they are named in the provided pipeline.
            When dict[str, str] is provided, current names will be
            mapped to new names in the resultant pipeline.
    Returns:
        A dictionary that maps the old parameter names to the provided ones.
    Examples:
        >>> _get_param_names_mapping("param_name")
        {"params:param_name": "params:param_name"}  # a str name will stay the same
        >>> _get_param_names_mapping(set(["param_1", "param_2"]))
        # a set[str] of names will stay the same
        {"params:param_1": "params:param_1", "params:param_2": "params:param_2"}
        >>> _get_param_names_mapping({"param_1": "new_name_for_param_1"})
        # a dict[str, str] of names will map key to valu
        {"params:param_1": "params:new_name_for_param_1"}
    """
    params = {}
    for name, new_name in _get_dataset_names_mapping(names).items():
        if _is_all_parameters(name):
            params[name] = name  # don't map parameters into params:parameters
        else:
            param_name = _normalize_param_name(name)
            param_new_name = _normalize_param_name(new_name)
            params[param_name] = param_new_name
    return params


def pipeline(  # noqa: too-many-arguments
    pipe: Iterable[Node | Pipeline] | Pipeline,
    *,
    inputs: str | set[str] | dict[str, str] | None = None,
    outputs: str | set[str] | dict[str, str] | None = None,
    parameters: str | set[str] | dict[str, str] | None = None,
    tags: str | Iterable[str] | None = None,
    namespace: str = None,
) -> Pipeline:
    r"""Create a ``Pipeline`` from a collection of nodes and/or ``Pipeline``\s.

    Args:
        pipe: The nodes the ``Pipeline`` will be made of. If you
            provide pipelines among the list of nodes, those pipelines will
            be expanded and all their nodes will become part of this
            new pipeline.
        inputs: A name or collection of input names to be exposed as connection points
            to other pipelines upstream. This is optional; if not provided, the
            pipeline inputs are automatically inferred from the pipeline structure.
            When str or set[str] is provided, the listed input names will stay
            the same as they are named in the provided pipeline.
            When dict[str, str] is provided, current input names will be
            mapped to new names.
            Must only refer to the pipeline's free inputs.
        outputs: A name or collection of names to be exposed as connection points
            to other pipelines downstream. This is optional; if not provided, the
            pipeline inputs are automatically inferred from the pipeline structure.
            When str or set[str] is provided, the listed output names will stay
            the same as they are named in the provided pipeline.
            When dict[str, str] is provided, current output names will be
            mapped to new names.
            Can refer to both the pipeline's free outputs, as well as
            intermediate results that need to be exposed.
        parameters: A name or collection of parameters to namespace.
            When str or set[str] are provided, the listed parameter names will stay
            the same as they are named in the provided pipeline.
            When dict[str, str] is provided, current parameter names will be
            mapped to new names.
            The parameters can be specified without the `params:` prefix.
        tags: Optional set of tags to be applied to all the pipeline nodes.
        namespace: A prefix to give to all dataset names,
            except those explicitly named with the `inputs`/`outputs`
            arguments, and parameter references (`params:` and `parameters`).

    Raises:
        ModularPipelineError: When inputs, outputs or parameters are incorrectly
            specified, or they do not exist on the original pipeline.
        ValueError: When underlying pipeline nodes inputs/outputs are not
            any of the expected types (str, dict, list, or None).

    Returns:
        A new ``Pipeline`` object.
    """
    if isinstance(pipe, Pipeline):
        # To ensure that we are always dealing with a *copy* of pipe.
        pipe = Pipeline([pipe], tags=tags)
    else:
        pipe = Pipeline(pipe, tags=tags)

    if not any([inputs, outputs, parameters, namespace]):
        return pipe

    # noqa: protected-access
    inputs = _get_dataset_names_mapping(inputs)
    outputs = _get_dataset_names_mapping(outputs)
    parameters = _get_param_names_mapping(parameters)

    _validate_datasets_exist(inputs.keys(), outputs.keys(), parameters.keys(), pipe)
    _validate_inputs_outputs(inputs.keys(), outputs.keys(), pipe)

    mapping = {**inputs, **outputs, **parameters}

    def _prefix_dataset(name: str) -> str:
        return f"{namespace}.{name}"

    def _prefix_param(name: str) -> str:
        _, param_name = name.split("params:")
        return f"params:{namespace}.{param_name}"

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
            # if name refers to the set of all "parameters", leave as is
            (_is_all_parameters, lambda n: n),
            # if transcode base is mapped to a new name, update with new base
            (_is_transcode_base_in_mapping, _map_transcode_base),
            # if name refers to a single parameter and a namespace is given, apply prefix
            (lambda n: bool(namespace) and _is_single_parameter(n), _prefix_param),
            # if namespace given for a dataset, prefix name using that namespace
            (lambda n: bool(namespace), _prefix_dataset),
        ]

        for predicate, processor in rules:
            if predicate(name):
                return processor(name)

        # leave name as is
        return name

    def _process_dataset_names(
        datasets: None | str | list[str] | dict[str, str]
    ) -> None | str | list[str] | dict[str, str]:
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

    return Pipeline(new_nodes, tags=tags)
