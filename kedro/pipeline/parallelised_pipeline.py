# Copyright 2021 QuantumBlack Visual Analytics Limited
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
"""Allow to reuse pipelines for similar task by replicating and parameterising
nodes or filtering input datasets"""


import collections
import functools
import itertools
import warnings
from typing import Callable, Dict, Iterable, List

import pandas

from kedro.pipeline import Pipeline, node, pipeline


def parallelised_pipeline(
    pipe: Pipeline,
    scenarios: Dict[str, Iterable],
    filters: Dict[str, Iterable] = None,
    aggregate_all: bool = True,
):
    """
    Create a new parallelised pipeline with all the possible scenario combinations
    as sub-pipelines replication of the original `pipe`.

    Args:
        pipe (Pipeline): The pipeline to duplicate by iterating through all the
            scenario combinations.
        scenarios (Dict[str, Iterable]): scenarios with their possible values.
            Iteration will be over the product space of all scenarios.
        filters (Dict[str, Iterable], optional): Instead of special input parameters
            to the node functions filter the specified input datasets. One column name
            is necessary for all scenario to filter on. Defaults to None.
        aggregate_all (bool, optional): Aggregate all output datasets or only
            those that are part of the final output of the original pipeline. Defaults
            to False.

    Returns:
        Pipeline: The paralellised pipeline containing sub-pipelines for all the
        scenario combinations and a synthetic aggregator node connecting them.
        Another synthetic node is added in the beginning if filters are specified.

    Example:
    ::

        >>> parallelised_pipeline(
        >>>     nodes,
        >>>     scenarios = {
        >>>       'scenario1': ['low', 'med', 'high'],
        >>>       'other_scenario': ['red', 'green', 'blue'],
        >>>     },
        >>>     filters = {
        >>>       'input_dataset_name': ['filter_on_column_for_scenario1', 'column_for_other']
        >>>     aggregate_all_outputs = False,
        >>> )

    """
    pipes = []  # type List[Any]
    outputs_to_aggregate = []  # type: List[str]
    inputs_to_generate = []  # type: List[str]
    # creates :math:`\prod{len(scenario_i)}` number of copies from nodes
    # generate parameter space
    for combination in itertools.product(*scenarios.values()):
        combination_dict = dict(zip(scenarios.keys(), combination))
        short_name = _short_name(combination)

        new_pipe = pipe.tag(str(combination_dict).replace("'", ""))
        if filters is None:
            new_pipe = _replicate_pipeline(new_pipe, combination_dict)
        else:
            new_pipe = _replicate_pipeline_with_filters(
                new_pipe, combination_dict, filters
            )

            # filter node will take original inputs and generate
            inputs_to_generate += [short_name + "." + inp for inp in filters.keys()]

        outputs_to_aggregate += sorted(
            list(new_pipe.all_outputs() if aggregate_all else new_pipe.outputs())
        )

        pipes.append(new_pipe)

    # final outputs aggregated under the original name
    aggregate_to = sorted(list(pipe.all_outputs() if aggregate_all else pipe.outputs()))

    aggregator_node = node(
        func=functools.partial(
            _aggregator, scenarios=scenarios, aggregate_to=aggregate_to
        ),
        inputs=outputs_to_aggregate,
        outputs=aggregate_to,
        name=f"Aggregator_for-{'_'.join(aggregate_to)}",
        tags=["aggregators"],
    )

    if filters is not None:
        filter_node = node(
            func=functools.partial(_filterer, scenarios=scenarios, filters=filters),
            inputs=list(filters.keys()),
            outputs=inputs_to_generate,
            name=f"Filterer_for-{'_'.join(filters.keys())}",
            tags=["filterers"],
        )
        return Pipeline([filter_node, *pipes, aggregator_node])

    return Pipeline([*pipes, aggregator_node])


def parallelisation_setup(
    scenarios: Dict[str, Iterable], filter_datasets: Dict[str, Iterable],
) -> Callable:
    """Decorator to setup parallelisation for a function
    that returns a pipeline (typical for Kedro's modular
    pipelines).

    Args:
        scenarios (Iterable[str]): Scenarios to apply defined in the parameter
            `parallelisation_setup`.
        filter_datasets (Dict[str, Iterable]): Datasets to filter should match the
            input for :func:`aggregator_pipeline`.

    Returns:
        Callable: The decorator to use.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwds):
            pipe = func(*args, **kwds)
            return parallelised_pipeline(
                pipe, scenarios=scenarios, filters=filter_datasets,
            )

        return wrapper

    return decorator


def _short_name(lst):
    return "_".join([val.lower() if isinstance(val, str) else str(val) for val in lst])


def _aggregator(*args, scenarios, aggregate_to):
    """Aggregate all inputs along combinations

    Merge all prefixed outputs into the unprefixed version.
    """
    inputs = collections.deque(args)
    outputs = collections.defaultdict(pandas.DataFrame)
    for _ in itertools.product(*scenarios.values()):
        # TODO add plugable aggregators here
        for output in aggregate_to:
            outputs[output] = outputs[output].append(inputs.popleft())
    return tuple(outputs.values())


def _filterer(*args, scenarios, filters):
    """Take original inputs and generate all filtered inputs
    necessary for the replicated nodes
    """
    inputs = dict(zip(filters.keys(), args))
    outputs = {}
    for combination in itertools.product(*scenarios.values()):
        short_name = _short_name(combination)
        for input_name, filter_cols in filters.items():
            # TODO add possibility to use custom filtering
            frame = inputs[input_name].copy()

            for colname, val in zip(filter_cols, combination):
                frame = frame[frame[colname] == val]
                # TODO filter only if the colname is not None
                if frame.shape[0] == 0:
                    warnings.warn(
                        f"{input_name} was filtered to empty dataset on {colname} == {val}"
                    )
            outputs[short_name + "." + input_name] = frame
    return tuple(outputs.values())


def _replicate_pipeline(pipe, combination_dict):
    short_name = _short_name(combination_dict.values())

    # decorator method is not working with `ParallelRunner`
    for nnode in pipe.nodes:
        nnode.func = functools.partial(nnode.func, **combination_dict)

    return pipeline(
        pipe, inputs={inp: inp for inp in pipe.inputs()}, namespace=short_name,
    )


def _replicate_pipeline_with_filters(pipe, combination_dict, filters):
    short_name = _short_name(combination_dict.values())

    return pipeline(
        pipe,
        inputs={inp: inp for inp in pipe.inputs() if inp not in filters.keys()},
        namespace=short_name,
    )
