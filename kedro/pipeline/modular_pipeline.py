# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""Helper to integrate modular pipelines into a master pipeline."""
import copy
from typing import AbstractSet, Dict, List, Union

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
            "Failed to map datasets and/or parameters: {}".format(
                ", ".join(sorted(non_existent))
            )
        )


def pipeline(
    pipe: Pipeline,
    *,
    inputs: Dict[str, str] = None,
    outputs: Dict[str, str] = None,
    parameters: Dict[str, str] = None,
    namespace: str = None,
) -> Pipeline:
    """Create a copy of the pipeline and its nodes,
    with some dataset names and node names modified.

    Args:
        pipe: Original modular pipeline to integrate
        inputs: A map of the existing input name to the new one.
            Must only refer to the pipeline's free inputs.
        outputs: A map of the existing output name to the new one.
            Can refer to both the pipeline's free outputs, as well
            as intermediate results that need to be exposed.
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
    inputs = copy.deepcopy(inputs) or {}
    outputs = copy.deepcopy(outputs) or {}
    parameters = copy.deepcopy(parameters) or {}

    _validate_datasets_exist(inputs.keys(), outputs.keys(), parameters.keys(), pipe)
    _validate_inputs_outputs(inputs.keys(), outputs.keys(), pipe)

    mapping = {**inputs, **outputs, **parameters}

    def _prefix(name: str) -> str:
        return "{}.{}".format(namespace, name) if namespace else name

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
            "Unexpected input {} of type {}".format(datasets, type(datasets))
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
