"""Helper to integrate modular pipelines into a master pipeline."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from kedro import KedroDeprecationWarning
from kedro.pipeline.pipeline import (
    Pipeline,
    _get_dataset_names_mapping,
    _get_param_names_mapping,
    _is_all_parameters,
    _is_single_parameter,
    _validate_datasets_exist,
    _validate_inputs_outputs,
)

from .transcoding import TRANSCODING_SEPARATOR, _transcode_split

if TYPE_CHECKING:
    from collections.abc import Iterable

    from kedro.pipeline.node import Node

from .pipeline import ModularPipelineError

__all__ = ["ModularPipelineError"]

warnings.warn(
    "The `kedro.pipeline.modular_pipeline` module is deprecated and will be removed "
    "in Kedro 1.0.0. Please use `kedro.pipeline.pipeline` instead.",
    KedroDeprecationWarning,
    stacklevel=2,
)


def pipeline(  # noqa: PLR0913
    pipe: Iterable[Node | Pipeline] | Pipeline,
    *,
    inputs: str | set[str] | dict[str, str] | None = None,
    outputs: str | set[str] | dict[str, str] | None = None,
    parameters: str | set[str] | dict[str, str] | None = None,
    tags: str | Iterable[str] | None = None,
    namespace: str | None = None,
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
            pipeline outputs are automatically inferred from the pipeline structure.
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

    def _map_transcode_base(name: str) -> str:
        base_name, transcode_suffix = _transcode_split(name)
        return TRANSCODING_SEPARATOR.join((mapping[base_name], transcode_suffix))

    def _rename(name: str) -> str:
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
            if predicate(name):  # type: ignore[no-untyped-call]
                processor_name: str = processor(name)  # type: ignore[no-untyped-call]
                return processor_name

        # leave name as is
        return name

    def _process_dataset_names(
        datasets: str | list[str] | dict[str, str] | None,
    ) -> str | list[str] | dict[str, str] | None:
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

        node_copy: Node = node._copy(
            inputs=_process_dataset_names(node._inputs),
            outputs=_process_dataset_names(node._outputs),
            namespace=new_namespace,
            confirms=_process_dataset_names(node._confirms),
        )
        return node_copy

    new_nodes = [_copy_node(n) for n in pipe.nodes]

    return Pipeline(new_nodes, tags=tags)
