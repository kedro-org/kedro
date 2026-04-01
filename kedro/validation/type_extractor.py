"""Type extractor for extracting type hints from pipeline node signatures."""

from __future__ import annotations

import dataclasses
import inspect
import logging
import types
from typing import TYPE_CHECKING, Union, get_args, get_origin, get_type_hints

from .utils import is_pydantic_class

if TYPE_CHECKING:
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node

logger = logging.getLogger(__name__)

_PARAMS_PREFIX = "params:"


def _unwrap_optional(tp: type) -> type:
    """Unwrap ``Optional[X]`` / ``X | None`` to ``X``.

    If the type is a union of exactly one non-None type and ``NoneType``,
    return the non-None type. Otherwise return the original type unchanged.
    """
    origin = get_origin(tp)
    if origin is Union or isinstance(tp, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


class TypeExtractor:
    """Extracts parameter type requirements from pipeline node signatures."""

    def __init__(self, pipelines: dict[str, Pipeline]) -> None:
        """Initialise the type extractor.

        Args:
            pipelines: Dictionary of registered pipelines to inspect.
        """
        self._pipelines = pipelines

    def extract_types_from_pipelines(self) -> dict[str, type]:
        """Extract all type requirements from registered pipelines.

        Walks all pipelines (except ``__default__``) and inspects node
        function signatures for type-annotated ``params:`` inputs.

        Returns:
            Dictionary mapping parameter keys to their expected types.
        """
        all_type_requirements: dict[str, type] = {}

        for pipeline_name, pipeline in self._pipelines.items():
            if pipeline_name == "__default__":
                continue

            pipeline_type_requirements = self._extract_types_from_pipeline(pipeline)

            for key, new_type in pipeline_type_requirements.items():
                if key in all_type_requirements:
                    existing_type = all_type_requirements[key]
                    if existing_type != new_type:
                        logger.warning(
                            "Conflicting type requirements for parameter '%s': "
                            "%s (existing) vs %s (from pipeline '%s'). "
                            "Using %s.",
                            key,
                            getattr(existing_type, "__name__", str(existing_type)),
                            getattr(new_type, "__name__", str(new_type)),
                            pipeline_name,
                            getattr(new_type, "__name__", str(new_type)),
                        )

            all_type_requirements.update(pipeline_type_requirements)

        logger.debug(
            "Found %d type requirements across all pipelines",
            len(all_type_requirements),
        )
        return all_type_requirements

    def _extract_types_from_pipeline(self, pipeline: Pipeline) -> dict[str, type]:
        """Extract type requirements from a single pipeline."""
        type_requirements: dict[str, type] = {}

        for node in getattr(pipeline, "nodes", []):
            node_type_requirements = self._extract_types_from_node(node)
            type_requirements.update(node_type_requirements)

        return type_requirements

    def _extract_types_from_node(self, node: Node) -> dict[str, type]:
        """Extract typed parameter requirements from a single node.

        Inspects the node's function signature and maps type-annotated
        ``params:`` inputs to their expected types.
        """
        func = getattr(node, "func", None)
        if func is None:
            return {}

        try:
            sig = inspect.signature(func)
            type_hints = get_type_hints(func, include_extras=False)
        except Exception as exc:
            logger.warning(
                "Could not extract type hints from function %s: %s",
                getattr(func, "__name__", repr(func)),
                exc,
            )
            return {}

        dataset_to_arg = self._build_dataset_to_arg_mapping(node, sig)

        all_requirements: dict[str, type] = {}

        for ds_name, arg_name in dataset_to_arg.items():
            expected_type = type_hints.get(arg_name)
            if not expected_type:
                continue

            if not ds_name.startswith(_PARAMS_PREFIX):
                continue

            # Unwrap Optional[X] / X | None so we validate against the inner type
            expected_type = _unwrap_optional(expected_type)

            # Only record types we can actually validate (Pydantic models or dataclasses)
            if not (
                is_pydantic_class(expected_type)
                or dataclasses.is_dataclass(expected_type)
            ):
                continue

            param_key = ds_name.split(":", 1)[1]
            all_requirements[param_key] = expected_type
            logger.debug(
                "Found parameter requirement: %s -> %s",
                param_key,
                getattr(expected_type, "__name__", str(expected_type)),
            )

        return all_requirements

    @staticmethod
    def _build_dataset_to_arg_mapping(
        node: Node, signature: inspect.Signature
    ) -> dict[str, str]:
        """Build mapping from dataset names to function argument names.

        Node inputs can be a list/tuple (positionally mapped) or a dict
        (explicitly mapped). This normalises both into ``{dataset: arg_name}``.
        """
        dataset_to_arg: dict[str, str] = {}
        node_inputs = getattr(node, "inputs", None)

        if isinstance(node_inputs, dict):
            dataset_to_arg.update(node_inputs)
        elif isinstance(node_inputs, list | tuple):
            sig_param_names = list(signature.parameters.keys())
            for idx, ds in enumerate(node_inputs):
                if idx < len(sig_param_names):
                    dataset_to_arg[ds] = sig_param_names[idx]

        return dataset_to_arg
