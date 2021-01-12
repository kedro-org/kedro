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
"""This module provides user-friendly functions for creating nodes as parts
of Kedro pipelines.
"""
import copy
import inspect
import logging
import re
from collections import Counter
from functools import reduce
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Union
from warnings import warn


class Node:  # pylint: disable=too-many-instance-attributes
    """``Node`` is an auxiliary class facilitating the operations required to
    run user-provided functions as part of Kedro pipelines.
    """

    def __init__(
        self,
        func: Callable,
        inputs: Union[None, str, List[str], Dict[str, str]],
        outputs: Union[None, str, List[str], Dict[str, str]],
        *,
        name: str = None,
        tags: Union[str, Iterable[str]] = None,
        decorators: Iterable[Callable] = None,
        confirms: Union[str, List[str]] = None,
        namespace: str = None,
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
            confirms: Optional name or the list of the names of the datasets
                that should be confirmed. This will result in calling
                ``confirm()`` method of the corresponding data set instance.
                Specified dataset names do not necessarily need to be present
                in the node ``inputs`` or ``outputs``.
            namespace: Optional node namespace.

        Raises:
            ValueError: Raised in the following cases:
                a) When the provided arguments do not conform to
                the format suggested by the type hint of the argument.
                b) When the node produces multiple outputs with the same name.
                c) When an input has the same name as an output.
                d) When the given node name violates the requirements:
                it must contain only letters, digits, hyphens, underscores
                and/or fullstops.

        """

        if not callable(func):
            raise ValueError(
                _node_error_message(
                    f"first argument must be a function, not `{type(func).__name__}`."
                )
            )

        if inputs and not isinstance(inputs, (list, dict, str)):
            raise ValueError(
                _node_error_message(
                    f"`inputs` type must be one of [String, List, Dict, None], "
                    f"not `{type(inputs).__name__}`."
                )
            )

        if outputs and not isinstance(outputs, (list, dict, str)):
            raise ValueError(
                _node_error_message(
                    f"`outputs` type must be one of [String, List, Dict, None], "
                    f"not `{type(outputs).__name__}`."
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
        if name and not re.match(r"[\w\.-]+$", name):
            raise ValueError(
                f"'{name}' is not a valid node name. It must contain only "
                f"letters, digits, hyphens, underscores and/or fullstops."
            )
        self._name = name
        self._namespace = namespace
        self._tags = set(_to_list(tags))
        self._decorators = list(decorators or [])

        self._validate_unique_outputs()
        self._validate_inputs_dif_than_outputs()
        self._confirms = confirms

    def _copy(self, **overwrite_params):
        """
        Helper function to copy the node, replacing some values.
        """
        params = {
            "func": self._func,
            "inputs": self._inputs,
            "outputs": self._outputs,
            "name": self._name,
            "namespace": self._namespace,
            "tags": self._tags,
            "decorators": self._decorators,
            "confirms": self._confirms,
        }
        params.update(overwrite_params)
        return Node(**params)

    @property
    def _logger(self):
        return logging.getLogger(__name__)

    @property
    def _unique_key(self):
        def hashable(value):
            if isinstance(value, dict):
                return tuple(sorted(value.items()))
            if isinstance(value, list):
                return tuple(value)
            return value

        return (self.name, hashable(self._inputs), hashable(self._outputs))

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return self._unique_key == other._unique_key

    def __lt__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return self._unique_key < other._unique_key

    def __hash__(self):
        return hash(self._unique_key)

    def __str__(self):
        def _sorted_set_to_str(xset):
            return f"[{','.join(sorted(xset))}]"

        out_str = _sorted_set_to_str(self.outputs) if self._outputs else "None"
        in_str = _sorted_set_to_str(self.inputs) if self._inputs else "None"

        prefix = self._name + ": " if self._name else ""
        return prefix + f"{self._func_name}({in_str}) -> {out_str}"

    def __repr__(self):  # pragma: no cover
        return "Node({}, {!r}, {!r}, {!r})".format(
            self._func_name, self._inputs, self._outputs, self._name
        )

    def __call__(self, **kwargs) -> Dict[str, Any]:
        return self.run(inputs=kwargs)

    @property
    def _func_name(self) -> str:
        name = _get_readable_func_name(self._func)
        if name == "<partial>":
            warn(
                f"The node producing outputs `{self.outputs}` is made from a `partial` function. "
                f"Partial functions do not have a `__name__` attribute: consider using "
                f"`functools.update_wrapper` for better log messages."
            )
        return name

    @property
    def func(self) -> Callable:
        """Exposes the underlying function of the node.

        Returns:
           Return the underlying function of the node.
        """
        return self._func

    @func.setter
    def func(self, func: Callable):
        """Sets the underlying function of the node.
        Useful if user wants to decorate the function in a node's Hook implementation.

        Args:
            func: The new function for node's execution.
        """
        self._func = func

    @property
    def tags(self) -> Set[str]:
        """Return the tags assigned to the node.

        Returns:
            Return the set of all assigned tags to the node.

        """
        return set(self._tags)

    def tag(self, tags: Union[str, Iterable[str]]) -> "Node":
        """Create a new ``Node`` which is an exact copy of the current one,
            but with more tags added to it.

        Args:
            tags: The tags to be added to the new node.

        Returns:
            A copy of the current ``Node`` object with the tags added.

        """
        return self._copy(tags=self.tags | set(_to_list(tags)))

    @property
    def name(self) -> str:
        """Node's name.

        Returns:
            Node's name if provided or the name of its function.
        """
        node_name = self._name or str(self)
        if self.namespace:
            return f"{self.namespace}.{node_name}"
        return node_name

    @property
    def short_name(self) -> str:
        """Node's name.

        Returns:
            Returns a short, user-friendly name that is not guaranteed to be unique.
            The namespace is stripped out of the node name.
        """
        if self._name:
            return self._name

        return self._func_name.replace("_", " ").title()

    @property
    def namespace(self) -> Optional[str]:
        """Node's namespace.

        Returns:
            String representing node's namespace, typically from outer to inner scopes.
        """
        return self._namespace

    @property
    def inputs(self) -> List[str]:
        """Return node inputs as a list, in the order required to bind them properly to
        the node's function.

        Returns:
            Node input names as a list.

        """
        if isinstance(self._inputs, dict):
            return _dict_inputs_to_list(self._func, self._inputs)
        return _to_list(self._inputs)

    @property
    def outputs(self) -> List[str]:
        """Return node outputs as a list preserving the original order
            if possible.

        Returns:
            Node output names as a list.

        """
        return _to_list(self._outputs)

    @property
    def confirms(self) -> List[str]:
        """Return dataset names to confirm as a list.

        Returns:
            Dataset names to confirm as a list.
        """
        return _to_list(self._confirms)

    @property
    def _decorated_func(self):
        return reduce(lambda g, f: f(g), self._decorators, self._func)

    def decorate(self, *decorators: Callable) -> "Node":
        """Create a new ``Node`` by applying the provided decorators to the
        underlying function. If no decorators are passed, it will return a
        new ``Node`` object, but with no changes to the function.

        Args:
            decorators: Decorators to be applied on the node function.
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
        warn(
            "The node's `decorate` API will be deprecated in Kedro 0.18.0."
            "Please use a node's Hooks to extend the node's behaviour in a pipeline."
            "For more information, please visit"
            "https://kedro.readthedocs.io/en/stable/07_extend_kedro/04_hooks.html",
            DeprecationWarning,
        )
        return self._copy(decorators=self._decorators + list(reversed(decorators)))

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
        self._logger.info("Running node: %s", str(self))

        outputs = None

        if not (inputs is None or isinstance(inputs, dict)):
            raise ValueError(
                f"Node.run() expects a dictionary or None, "
                f"but got {type(inputs)} instead"
            )

        try:
            inputs = dict() if inputs is None else inputs
            if not self._inputs:
                outputs = self._run_with_no_inputs(inputs)
            elif isinstance(self._inputs, str):
                outputs = self._run_with_one_input(inputs, self._inputs)
            elif isinstance(self._inputs, list):
                outputs = self._run_with_list(inputs, self._inputs)
            elif isinstance(self._inputs, dict):
                outputs = self._run_with_dict(inputs, self._inputs)

            return self._outputs_to_dictionary(outputs)

        # purposely catch all exceptions
        except Exception as exc:
            self._logger.error("Node `%s` failed with error: \n%s", str(self), str(exc))
            raise exc

    def _run_with_no_inputs(self, inputs: Dict[str, Any]):
        if inputs:
            raise ValueError(
                "Node {} expected no inputs, "
                "but got the following {} input(s) instead: {}".format(
                    str(self), len(inputs), list(sorted(inputs.keys()))
                )
            )

        return self._decorated_func()

    def _run_with_one_input(self, inputs: Dict[str, Any], node_input: str):
        if len(inputs) != 1 or node_input not in inputs:
            raise ValueError(
                "Node {} expected one input named '{}', "
                "but got the following {} input(s) instead: {}".format(
                    str(self), node_input, len(inputs), list(sorted(inputs.keys()))
                )
            )

        return self._decorated_func(inputs[node_input])

    def _run_with_list(self, inputs: Dict[str, Any], node_inputs: List[str]):
        # Node inputs and provided run inputs should completely overlap
        if set(node_inputs) != set(inputs.keys()):
            raise ValueError(
                "Node {} expected {} input(s) {}, "
                "but got the following {} input(s) instead: {}.".format(
                    str(self),
                    len(node_inputs),
                    node_inputs,
                    len(inputs),
                    list(sorted(inputs.keys())),
                )
            )
        # Ensure the function gets the inputs in the correct order
        return self._decorated_func(*[inputs[item] for item in node_inputs])

    def _run_with_dict(self, inputs: Dict[str, Any], node_inputs: Dict[str, str]):
        # Node inputs and provided run inputs should completely overlap
        if set(node_inputs.values()) != set(inputs.keys()):
            raise ValueError(
                "Node {} expected {} input(s) {}, "
                "but got the following {} input(s) instead: {}.".format(
                    str(self),
                    len(set(node_inputs.values())),
                    list(sorted(set(node_inputs.values()))),
                    len(inputs),
                    list(sorted(inputs.keys())),
                )
            )
        kwargs = {arg: inputs[alias] for arg, alias in node_inputs.items()}
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
            if not isinstance(outputs, (list, tuple)):
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
                f"Failed to save outputs of node {self}.\n"
                f"The node output is a dictionary, whereas the "
                f"function output is not."
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
                inspect.signature(func, follow_wrapped=False).bind(*args, **kwargs)
            except Exception as exc:
                func_args = inspect.signature(
                    func, follow_wrapped=False
                ).parameters.keys()
                func_name = _get_readable_func_name(func)

                raise TypeError(
                    f"Inputs of '{func_name}' function expected {list(func_args)}, "
                    f"but got {inputs}"
                ) from exc

    def _validate_unique_outputs(self):
        diff = Counter(self.outputs) - Counter(set(self.outputs))
        if diff:
            raise ValueError(
                f"Failed to create node {self} due to duplicate"
                f" output(s) {set(diff.keys())}.\nNode outputs must be unique."
            )

    def _validate_inputs_dif_than_outputs(self):
        common_in_out = set(self.inputs).intersection(set(self.outputs))
        if common_in_out:
            raise ValueError(
                f"Failed to create node {self}.\n"
                f"A node cannot have the same inputs and outputs: "
                f"{common_in_out}"
            )

    @staticmethod
    def _process_inputs_for_bind(inputs: Union[None, str, List[str], Dict[str, str]]):
        # Safeguard that we do not mutate list inputs
        inputs = copy.copy(inputs)
        args = []  # type: List[str]
        kwargs = {}  # type: Dict[str, str]
        if isinstance(inputs, str):
            args = [inputs]
        elif isinstance(inputs, list):
            args = inputs
        elif isinstance(inputs, dict):
            kwargs = inputs
        return args, kwargs


def _node_error_message(msg) -> str:
    return (
        "Invalid Node definition: {}\n"
        "Format should be: node(function, inputs, outputs)"
    ).format(msg)


def node(
    func: Callable,
    inputs: Union[None, str, List[str], Dict[str, str]],
    outputs: Union[None, str, List[str], Dict[str, str]],
    *,
    name: str = None,
    tags: Iterable[str] = None,
    confirms: Union[str, List[str]] = None,
    namespace: str = None,
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
        confirms: Optional name or the list of the names of the datasets
            that should be confirmed. This will result in calling ``confirm()``
            method of the corresponding data set instance. Specified dataset
            names do not necessarily need to be present in the node ``inputs``
            or ``outputs``.
        namespace: Optional node namespace.

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
    return Node(
        func,
        inputs,
        outputs,
        name=name,
        tags=tags,
        confirms=confirms,
        namespace=namespace,
    )


def _dict_inputs_to_list(func: Callable[[Any], Any], inputs: Dict[str, str]):
    """Convert a dict representation of the node inputs to a list, ensuring
    the appropriate order for binding them to the node's function.
    """
    sig = inspect.signature(func, follow_wrapped=False).bind(**inputs)
    return [*sig.args, *sig.kwargs.values()]


def _to_list(element: Union[None, str, Iterable[str], Dict[str, str]]) -> List:
    """Make a list out of node inputs/outputs.

    Returns:
        List[str]: Node input/output names as a list to standardise.
    """

    if element is None:
        return []
    if isinstance(element, str):
        return [element]
    if isinstance(element, dict):
        return sorted(element.values())
    return list(element)


def _get_readable_func_name(func: Callable) -> str:
    """Get a user-friendly readable name of the function provided.

    Returns:
        str: readable name of the provided callable func.
    """

    if hasattr(func, "__name__"):
        return func.__name__

    name = repr(func)
    if "functools.partial" in name:
        name = "<partial>"

    return name
