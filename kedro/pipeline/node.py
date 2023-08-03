"""This module provides user-friendly functions for creating nodes as parts
of Kedro pipelines.
"""
from __future__ import annotations

import copy
import inspect
import logging
import re
from collections import Counter
from typing import Any, Callable, Iterable
from warnings import warn

from more_itertools import spy, unzip


class Node:
    """``Node`` is an auxiliary class facilitating the operations required to
    run user-provided functions as part of Kedro pipelines.
    """

    def __init__(  # noqa: too-many-arguments
        self,
        func: Callable,
        inputs: None | str | list[str] | dict[str, str],
        outputs: None | str | list[str] | dict[str, str],
        *,
        name: str = None,
        tags: str | Iterable[str] | None = None,
        confirms: str | list[str] | None = None,
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
                function. When dict[str, str] is provided, variable names
                will be mapped to function argument names.
            outputs: The name or the list of the names of variables used
                as outputs to the function. The number of names should match
                the number of outputs returned by the provided function.
                When dict[str, str] is provided, variable names will be mapped
                to the named outputs the function returns.
            name: Optional node name to be used when displaying the node in
                logs or any other visualisations.
            tags: Optional set of tags to be applied to the node.
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
                    f"first argument must be a function, not '{type(func).__name__}'."
                )
            )

        if inputs and not isinstance(inputs, (list, dict, str)):
            raise ValueError(
                _node_error_message(
                    f"'inputs' type must be one of [String, List, Dict, None], "
                    f"not '{type(inputs).__name__}'."
                )
            )

        if outputs and not isinstance(outputs, (list, dict, str)):
            raise ValueError(
                _node_error_message(
                    f"'outputs' type must be one of [String, List, Dict, None], "
                    f"not '{type(outputs).__name__}'."
                )
            )

        if not inputs and not outputs:
            raise ValueError(
                _node_error_message("it must have some 'inputs' or 'outputs'.")
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
                # we sort it because a node with inputs/outputs
                # {"arg1": "a", "arg2": "b"} is equivalent to
                # a node with inputs/outputs {"arg2": "b", "arg1": "a"}
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
        def _set_to_str(xset):
            return f"[{';'.join(xset)}]"

        out_str = _set_to_str(self.outputs) if self._outputs else "None"
        in_str = _set_to_str(self.inputs) if self._inputs else "None"

        prefix = self._name + ": " if self._name else ""
        return prefix + f"{self._func_name}({in_str}) -> {out_str}"

    def __repr__(self):  # pragma: no cover
        return (
            f"Node({self._func_name}, {repr(self._inputs)}, {repr(self._outputs)}, "
            f"{repr(self._name)})"
        )

    def __call__(self, **kwargs) -> dict[str, Any]:
        return self.run(inputs=kwargs)

    @property
    def _func_name(self) -> str:
        name = _get_readable_func_name(self._func)
        if name == "<partial>":
            warn(
                f"The node producing outputs '{self.outputs}' is made from a 'partial' function. "
                f"Partial functions do not have a '__name__' attribute: consider using "
                f"'functools.update_wrapper' for better log messages."
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
    def tags(self) -> set[str]:
        """Return the tags assigned to the node.

        Returns:
            Return the set of all assigned tags to the node.

        """
        return set(self._tags)

    def tag(self, tags: str | Iterable[str]) -> Node:
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
    def namespace(self) -> str | None:
        """Node's namespace.

        Returns:
            String representing node's namespace, typically from outer to inner scopes.
        """
        return self._namespace

    @property
    def inputs(self) -> list[str]:
        """Return node inputs as a list, in the order required to bind them properly to
        the node's function.

        Returns:
            Node input names as a list.

        """
        if isinstance(self._inputs, dict):
            return _dict_inputs_to_list(self._func, self._inputs)
        return _to_list(self._inputs)

    @property
    def outputs(self) -> list[str]:
        """Return node outputs as a list preserving the original order
            if possible.

        Returns:
            Node output names as a list.

        """
        return _to_list(self._outputs)

    @property
    def confirms(self) -> list[str]:
        """Return dataset names to confirm as a list.

        Returns:
            Dataset names to confirm as a list.
        """
        return _to_list(self._confirms)

    def run(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
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
            inputs = {} if inputs is None else inputs
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
            self._logger.error(
                "Node %s failed with error: \n%s",
                str(self),
                str(exc),
                extra={"markup": True},
            )
            raise exc

    def _run_with_no_inputs(self, inputs: dict[str, Any]):
        if inputs:
            raise ValueError(
                f"Node {str(self)} expected no inputs, "
                f"but got the following {len(inputs)} input(s) instead: "
                f"{sorted(inputs.keys())}."
            )

        return self._func()

    def _run_with_one_input(self, inputs: dict[str, Any], node_input: str):
        if len(inputs) != 1 or node_input not in inputs:
            raise ValueError(
                f"Node {str(self)} expected one input named '{node_input}', "
                f"but got the following {len(inputs)} input(s) instead: "
                f"{sorted(inputs.keys())}."
            )

        return self._func(inputs[node_input])

    def _run_with_list(self, inputs: dict[str, Any], node_inputs: list[str]):
        # Node inputs and provided run inputs should completely overlap
        if set(node_inputs) != set(inputs.keys()):
            raise ValueError(
                f"Node {str(self)} expected {len(node_inputs)} input(s) {node_inputs}, "
                f"but got the following {len(inputs)} input(s) instead: "
                f"{sorted(inputs.keys())}."
            )
        # Ensure the function gets the inputs in the correct order
        return self._func(*(inputs[item] for item in node_inputs))

    def _run_with_dict(self, inputs: dict[str, Any], node_inputs: dict[str, str]):
        # Node inputs and provided run inputs should completely overlap
        if set(node_inputs.values()) != set(inputs.keys()):
            raise ValueError(
                f"Node {str(self)} expected {len(set(node_inputs.values()))} input(s) "
                f"{sorted(set(node_inputs.values()))}, "
                f"but got the following {len(inputs)} input(s) instead: "
                f"{sorted(inputs.keys())}."
            )
        kwargs = {arg: inputs[alias] for arg, alias in node_inputs.items()}
        return self._func(**kwargs)

    def _outputs_to_dictionary(self, outputs):
        def _from_dict():
            result, iterator = outputs, None
            # generator functions are lazy and we need a peek into their first output
            if inspect.isgenerator(outputs):
                (result,), iterator = spy(outputs)

            keys = list(self._outputs.keys())
            names = list(self._outputs.values())
            if not isinstance(result, dict):
                raise ValueError(
                    f"Failed to save outputs of node {self}.\n"
                    f"The node output is a dictionary, whereas the "
                    f"function output is {type(result)}."
                )
            if set(keys) != set(result.keys()):
                raise ValueError(
                    f"Failed to save outputs of node {str(self)}.\n"
                    f"The node's output keys {set(result.keys())} "
                    f"do not match with the returned output's keys {set(keys)}."
                )
            if iterator:
                exploded = map(lambda x: tuple(x[k] for k in keys), iterator)
                result = unzip(exploded)
            else:
                # evaluate this eagerly so we can reuse variable name
                result = tuple(result[k] for k in keys)
            return dict(zip(names, result))

        def _from_list():
            result, iterator = outputs, None
            # generator functions are lazy and we need a peek into their first output
            if inspect.isgenerator(outputs):
                (result,), iterator = spy(outputs)

            if not isinstance(result, (list, tuple)):
                raise ValueError(
                    f"Failed to save outputs of node {str(self)}.\n"
                    f"The node definition contains a list of "
                    f"outputs {self._outputs}, whereas the node function "
                    f"returned a '{type(result).__name__}'."
                )
            if len(result) != len(self._outputs):
                raise ValueError(
                    f"Failed to save outputs of node {str(self)}.\n"
                    f"The node function returned {len(result)} output(s), "
                    f"whereas the node definition contains {len(self._outputs)} "
                    f"output(s)."
                )

            if iterator:
                result = unzip(iterator)
            return dict(zip(self._outputs, result))

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
        cnt = Counter(self.outputs)
        diff = {k for k in cnt if cnt[k] > 1}
        if diff:
            raise ValueError(
                f"Failed to create node {self} due to duplicate "
                f"output(s) {diff}.\nNode outputs must be unique."
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
    def _process_inputs_for_bind(inputs: None | str | list[str] | dict[str, str]):
        # Safeguard that we do not mutate list inputs
        inputs = copy.copy(inputs)
        args: list[str] = []
        kwargs: dict[str, str] = {}
        if isinstance(inputs, str):
            args = [inputs]
        elif isinstance(inputs, list):
            args = inputs
        elif isinstance(inputs, dict):
            kwargs = inputs
        return args, kwargs


def _node_error_message(msg) -> str:
    return (
        f"Invalid Node definition: {msg}\n"
        f"Format should be: node(function, inputs, outputs)"
    )


def node(  # noqa: too-many-arguments
    func: Callable,
    inputs: None | str | list[str] | dict[str, str],
    outputs: None | str | list[str] | dict[str, str],
    *,
    name: str = None,
    tags: str | Iterable[str] | None = None,
    confirms: str | list[str] | None = None,
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
            dict[str, str] is provided, variable names will be mapped to
            function argument names.
        outputs: The name or the list of the names of variables used as outputs
            to the function. The number of names should match the number of
            outputs returned by the provided function. When dict[str, str]
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
        >>>                boats: pd.DataFrame) -> dict[str, pd.DataFrame]:
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


def _dict_inputs_to_list(func: Callable[[Any], Any], inputs: dict[str, str]):
    """Convert a dict representation of the node inputs to a list, ensuring
    the appropriate order for binding them to the node's function.
    """
    sig = inspect.signature(func, follow_wrapped=False).bind(**inputs)
    return [*sig.args, *sig.kwargs.values()]


def _to_list(element: None | str | Iterable[str] | dict[str, str]) -> list[str]:
    """Make a list out of node inputs/outputs.

    Returns:
        list[str]: Node input/output names as a list to standardise.
    """

    if element is None:
        return []
    if isinstance(element, str):
        return [element]
    if isinstance(element, dict):
        return list(element.values())
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
