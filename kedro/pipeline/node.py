# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module provides user-friendly functions for creating nodes as parts
of Kedro pipelines.
"""
import copy
import inspect
import logging
from collections import Counter
from functools import reduce
from typing import Any, Callable, Dict, Iterable, List, Set, Union


class Node:
    """``Node`` is an auxiliary class facilitating the operations required to
    run user-provided functions as part of Kedro pipelines.
    """

    # pylint: disable=W9016
    def __init__(
        self,
        func: Callable,
        inputs: Union[None, str, List[str], Dict[str, str]],
        outputs: Union[None, str, List[str], Dict[str, str]],
        *,
        name: str = None,
        tags: Iterable[str] = None,
        decorators: Iterable[Callable] = None
    ):
        """Create a node in the pipeline by providing a function to be called
        along with variable names for inputs and/or outputs.

        Args:
            func: A function that corresponds to the node logic.
                The function should have at least one input or output.
            inputs: The name or the list of the names of variables used as
                inputs to the function. The number of names should match
                the number of arguments in the definition of the provided
                function. When Dict[str, str] is provided, variable names
                will be mapped to function argument names.
            outputs: The name or the list of the names of variables used
                as outputs to the function. The number of names should match
                the number of outputs returned by the provided function.
                When Dict[str, str] is provided, variable names will be mapped
                to the named outputs the function returns.
            name: Optional node name to be used when displaying the node in
                logs or any other visualisations.
            tags: Optional set of tags to be applied to the node.
            decorators: Optional list of decorators to be applied to the node.

        Raises:
            ValueError: Raised in the following cases:
                a) When the provided arguments do not conform to
                the format suggested by the type hint of the argument.
                b) When the node produces multiple outputs with the same name.
                c) An input has the same name as an output.

        """

        if not callable(func):
            raise ValueError(
                _node_error_message(
                    "first argument must be a "
                    "function, not `{}`.".format(type(func).__name__)
                )
            )

        if inputs and not isinstance(inputs, (list, dict, str)):
            raise ValueError(
                _node_error_message(
                    "`inputs` type must be one of [String, List, Dict, None], "
                    "not `{}`.".format(type(inputs).__name__)
                )
            )

        if outputs and not isinstance(outputs, (list, dict, str)):
            raise ValueError(
                _node_error_message(
                    "`outputs` type must be one of [String, List, Dict, None], "
                    "not `{}`.".format(type(outputs).__name__)
                )
            )

        if not inputs and not outputs:
            raise ValueError(
                _node_error_message("it must have some `inputs` or `outputs`.")
            )

        self._validate_inputs(func, inputs)

        self._func = func
        self._inputs = inputs
        self._outputs = outputs
        self._name = name
        self._tags = set([] if tags is None else tags)
        self._decorators = decorators or []

        self._validate_unique_outputs()
        self._validate_inputs_dif_than_outputs()

    def tag(self, tags: Iterable[str]) -> "Node":
        """Create a new ``Node`` which is an exact copy of the current one,
            but with more tags added to it.

        Args:
            tags: The tags to be added to the new node.

        Returns:
            A copy of the current ``Node`` object with the tags added.

        """
        return Node(
            self._func,
            self._inputs,
            self._outputs,
            name=self._name,
            tags=set(self._tags) | set(tags),
            decorators=self._decorators,
        )

    @property
    def tags(self) -> Set[str]:
        """Return the tags assigned to the node.

        Returns:
            Return the set of all assigned tags to the node.

        """
        return set(self._tags)

    @property
    def _logger(self):
        return logging.getLogger(__name__)

    def decorate(self, *decorators: Callable) -> "Node":
        """Create a new ``Node`` by applying the provided decorators to the
        underlying function. If no decorators are passed, it will return a
        new ``Node`` object, but with no changes to the function.

        Args:
            decorators: List of decorators to be applied on the node function.
                Decorators will be applied from right to left.

        Returns:
            A new ``Node`` object with the decorators applied to the function.

        Example:
        ::

            >>>
            >>> from functools import wraps
            >>>
            >>>
            >>> def apply_f(func: Callable) -> Callable:
            >>>     @wraps(func)
            >>>     def with_f(*args, **kwargs):
            >>>         args = ["f({})".format(a) for a in args]
            >>>         return func(*args, **kwargs)
            >>>     return with_f
            >>>
            >>>
            >>> def apply_g(func: Callable) -> Callable:
            >>>     @wraps(func)
            >>>     def with_g(*args, **kwargs):
            >>>         args = ["g({})".format(a) for a in args]
            >>>         return func(*args, **kwargs)
            >>>     return with_g
            >>>
            >>>
            >>> def apply_h(func: Callable) -> Callable:
            >>>     @wraps(func)
            >>>     def with_h(*args, **kwargs):
            >>>         args = ["h({})".format(a) for a in args]
            >>>         return func(*args, **kwargs)
            >>>     return with_h
            >>>
            >>>
            >>> def apply_fg(func: Callable) -> Callable:
            >>>     @wraps(func)
            >>>     def with_fg(*args, **kwargs):
            >>>         args = ["fg({})".format(a) for a in args]
            >>>         return func(*args, **kwargs)
            >>>     return with_fg
            >>>
            >>>
            >>> def identity(value):
            >>>     return value
            >>>
            >>>
            >>> # using it as a regular python decorator
            >>> @apply_f
            >>> def decorated_identity(value):
            >>>     return value
            >>>
            >>>
            >>> # wrapping the node function
            >>> old_node = node(apply_g(decorated_identity), 'input', 'output',
            >>>                 name='node')
            >>> # using the .decorate() method to apply multiple decorators
            >>> new_node = old_node.decorate(apply_h, apply_fg)
            >>> result = new_node.run(dict(input=1))
            >>>
            >>> assert old_node.name == new_node.name
            >>> assert "output" in result
            >>> assert result['output'] == "f(g(fg(h(1))))"
        """
        decorators = self._decorators + list(reversed(decorators))
        return Node(
            self._func,
            self._inputs,
            self._outputs,
            name=self._name,
            tags=self.tags,
            decorators=decorators,
        )

    @property
    def name(self) -> str:  # pragma: no-cover
        """Node's name.

        Returns:
            Node's name if provided or the name of its function.
        """
        return self._name if self._name else str(self)

    @property
    def inputs(self) -> List[str]:
        """Return node inputs as a list preserving the original order
            if possible.

        Returns:
            Node input names as a list.

        """
        return self._to_list(self._inputs)

    @property
    def outputs(self) -> List[str]:
        """Return node outputs as a list preserving the original order
            if possible.

        Returns:
            Node output names as a list.

        """
        return self._to_list(self._outputs)

    @staticmethod
    def _to_list(element: Union[None, str, List[str], Dict[str, str]]) -> List:
        """Make a list out of node inputs/outputs.

        Returns:
            List[str]: Node input/output names as a list to standardise.
        """
        if element is None:
            return list()
        if isinstance(element, str):
            return [element]
        if isinstance(element, dict):
            return list(element.values())
        return element

    def run(self, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run this node using the provided inputs and return its results
        in a dictionary.

        Args:
            inputs: Dictionary of inputs as specified at the creation of
                the node.

        Raises:
            ValueError: In the following cases:
                a) The node function inputs are incompatible with the node
                input definition.
                Example 1: node definition input is a list of 2
                DataFrames, whereas only 1 was provided or 2 different ones
                were provided.
                b) The node function outputs are incompatible with the node
                output definition.
                Example 1: node function definition is a dictionary,
                whereas function returns a list.
                Example 2: node definition output is a list of 5
                strings, whereas the function returns a list of 4 objects.
            Exception: Any exception thrown during execution of the node.

        Returns:
            All produced node outputs are returned in a dictionary, where the
            keys are defined by the node outputs.

        """
        self._logger.debug("Running node: %s", str(self))

        outputs = None

        if not (inputs is None or isinstance(inputs, dict)):
            raise ValueError(
                "Node.run() expects a dictionary or None, "
                "but got {} instead".format(type(inputs))
            )

        try:
            inputs = dict() if inputs is None else inputs
            if not self._inputs:
                outputs = self._run_no_inputs(inputs)
            elif isinstance(self._inputs, str):
                outputs = self._run_one_input(inputs)
            elif isinstance(self._inputs, list):
                outputs = self._run_with_list(inputs)
            elif isinstance(self._inputs, dict):
                outputs = self._run_with_dict(inputs)

            return self._outputs_to_dictionary(outputs)

        # purposely catch all exceptions
        except Exception as exc:
            self._logger.error("Node `%s` failed with error: \n%s", str(self), str(exc))
            raise exc

    @property
    def _decorated_func(self):
        return reduce(lambda g, f: f(g), self._decorators, self._func)

    def _run_no_inputs(self, inputs: Dict[str, Any]):
        if inputs:
            raise ValueError(
                "Node {} expected no inputs, "
                "but got the following {} input(s) instead: {}".format(
                    str(self), len(inputs), list(sorted(inputs.keys()))
                )
            )

        return self._decorated_func()

    def _run_one_input(self, inputs: Dict[str, Any]):
        if len(inputs) != 1 or self._inputs not in inputs:
            raise ValueError(
                "Node {} expected one input named '{}', "
                "but got the following {} input(s) instead: {}".format(
                    str(self), self._inputs, len(inputs), list(sorted(inputs.keys()))
                )
            )

        return self._decorated_func(inputs[self._inputs])

    def _run_with_list(self, inputs: Dict[str, Any]):
        all_available = set(self._inputs).issubset(inputs.keys())
        if len(self._inputs) != len(inputs) or not all_available:
            # This can be split in future into two cases, one successful
            raise ValueError(
                "Node {} expected {} input(s) {}, "
                "but got the following {} input(s) instead: {}.".format(
                    str(self),
                    len(self._inputs),
                    self._inputs,
                    len(inputs),
                    list(sorted(inputs.keys())),
                )
            )
        # Ensure the function gets the inputs in the correct order
        return self._decorated_func(*[inputs[item] for item in self._inputs])

    def _run_with_dict(self, inputs: Dict[str, Any]):
        all_available = set(self._inputs.values()).issubset(inputs.keys())
        if len(set(self._inputs.values())) != len(inputs) or not all_available:
            # This can be split in future into two cases, one successful
            raise ValueError(
                "Node {} expected {} input(s) {}, "
                "but got the following {} input(s) instead: {}.".format(
                    str(self),
                    len(set(self._inputs.values())),
                    list(sorted(set(self._inputs.values()))),
                    len(inputs),
                    list(sorted(inputs.keys())),
                )
            )
        kwargs = {arg: inputs[alias] for arg, alias in self._inputs.items()}
        return self._decorated_func(**kwargs)

    def _outputs_to_dictionary(self, outputs):
        def _from_dict():
            if set(self._outputs.keys()) != set(outputs.keys()):
                raise ValueError(
                    "Failed to save outputs of node {}.\n"
                    "The node's output keys {} do not "
                    "match with the returned output's keys {}.".format(
                        str(self), set(outputs.keys()), set(self._outputs.keys())
                    )
                )
            return {name: outputs[key] for key, name in self._outputs.items()}

        def _from_list():
            if not isinstance(outputs, list):
                raise ValueError(
                    "Failed to save outputs of node {}.\n"
                    "The node definition contains a list of "
                    "outputs {}, whereas the node function "
                    "returned a `{}`.".format(
                        str(self), self._outputs, type(outputs).__name__
                    )
                )
            if len(outputs) != len(self._outputs):
                raise ValueError(
                    "Failed to save outputs of node {}.\n"
                    "The node function returned {} output(s), "
                    "whereas the node definition contains {} "
                    "output(s).".format(str(self), len(outputs), len(self._outputs))
                )

            return dict(zip(self._outputs, outputs))

        if isinstance(self._outputs, dict) and not isinstance(outputs, dict):
            raise ValueError(
                "Failed to save outputs of node {}.\n"
                "The node output is a dictionary, whereas the "
                "function output is not.".format(str(self))
            )

        if self._outputs is None:
            return {}
        if isinstance(self._outputs, str):
            return {self._outputs: outputs}
        if isinstance(self._outputs, dict):
            return _from_dict()
        return _from_list()

    def _validate_inputs(self, func, inputs):
        # inspect does not support built-in Python functions written in C.
        # Thus we only validate func if it is not built-in.
        if not inspect.isbuiltin(func):
            args, kwargs = self._process_inputs_for_bind(inputs)
            try:
                inspect.signature(func).bind(*args, **kwargs)
            except Exception as exc:
                func_args = inspect.signature(func).parameters.keys()
                raise TypeError(
                    "Inputs of function expected {}, but got {}".format(
                        str(list(func_args)), str(inputs)
                    )
                ) from exc

    @staticmethod
    def _process_inputs_for_bind(inputs: Union[None, str, List[str], Dict[str, str]]):
        # Safeguard that we do not mutate list inputs
        inputs = copy.copy(inputs)
        args = []
        kwargs = {}
        if isinstance(inputs, str):
            args = [inputs]
        elif isinstance(inputs, list):
            args = inputs
        elif isinstance(inputs, dict):
            kwargs = inputs
        return args, kwargs

    def _validate_unique_outputs(self):
        diff = Counter(self.outputs) - Counter(set(self.outputs))
        if diff:
            raise ValueError(
                "Failed to create node {} due to duplicate"
                " output(s) {}.\nNode outputs must be unique.".format(
                    str(self), set(diff.keys())
                )
            )

    def _validate_inputs_dif_than_outputs(self):
        common_in_out = set(self.inputs).intersection(set(self.outputs))
        if common_in_out:
            raise ValueError(
                "Failed to create node {}.\n"
                "A node cannot have the same inputs and outputs: "
                "{}".format(str(self), common_in_out)
            )

    def __str__(self):
        def _sorted_set_to_str(xset):
            return "[" + ",".join([name for name in sorted(xset)]) + "]"

        out_str = _sorted_set_to_str(self.outputs) if self._outputs else "None"
        in_str = _sorted_set_to_str(self.inputs) if self._inputs else "None"

        prefix = self._name + ": " if self._name else ""
        return prefix + "{}({}) -> {}".format(self._func.__name__, in_str, out_str)

    def __repr__(self):  # pragma: no cover
        return "Node({}, {!r}, {!r}, {!r})".format(
            self._func.__name__, self._inputs, self._outputs, self._name
        )

    def __eq__(self, other):  # pragma: no cover
        keys = {"_inputs", "_outputs", "_func", "_name"}
        return all(self.__dict__[k] == other.__dict__[k] for k in keys)

    def __hash__(self):
        return hash((tuple(self.inputs), tuple(self.outputs), self._name))


def _node_error_message(msg) -> str:
    return (
        "Invalid Node definition: {}\n"
        "Format should be: node(function, inputs, outputs)"
    ).format(msg)


def node(  # pylint: disable=W9016
    func: Callable,
    inputs: Union[None, str, List[str], Dict[str, str]],
    outputs: Union[None, str, List[str], Dict[str, str]],
    *,
    name: str = None,
    tags: Iterable[str] = None
) -> Node:
    """Create a node in the pipeline by providing a function to be called
    along with variable names for inputs and/or outputs.

    Args:
        func: A function that corresponds to the node logic. The function
            should have at least one input or output.
        inputs: The name or the list of the names of variables used as inputs
            to the function. The number of names should match the number of
            arguments in the definition of the provided function. When
            Dict[str, str] is provided, variable names will be mapped to
            function argument names.
        outputs: The name or the list of the names of variables used as outputs
            to the function. The number of names should match the number of
            outputs returned by the provided function. When Dict[str, str]
            is provided, variable names will be mapped to the named outputs the
            function returns.
        name: Optional node name to be used when displaying the node in logs or
            any other visualisations.
        tags: Optional set of tags to be applied to the node.

    Returns:
        A Node object with mapped inputs, outputs and function.

    Example:
    ::

        >>> import pandas as pd
        >>> import numpy as np
        >>>
        >>> def clean_data(cars: pd.DataFrame,
        >>>                boats: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        >>>     return dict(cars_df=cars.dropna(), boats_df=boats.dropna())
        >>>
        >>> def halve_dataframe(data: pd.DataFrame) -> List[pd.DataFrame]:
        >>>     return np.array_split(data, 2)
        >>>
        >>> nodes = [
        >>>     node(clean_data,
        >>>          inputs=['cars2017', 'boats2017'],
        >>>          outputs=dict(cars_df='clean_cars2017',
        >>>                       boats_df='clean_boats2017')),
        >>>     node(halve_dataframe,
        >>>          'clean_cars2017',
        >>>          ['train_cars2017', 'test_cars2017']),
        >>>     node(halve_dataframe,
        >>>          dict(data='clean_boats2017'),
        >>>          ['train_boats2017', 'test_boats2017'])
        >>> ]
    """
    return Node(func, inputs, outputs, name=name, tags=tags)
