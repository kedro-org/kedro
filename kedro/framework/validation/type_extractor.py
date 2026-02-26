"""Type extractor for extracting type hints from various sources."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, get_type_hints

from .exceptions import ValidationError

if TYPE_CHECKING:
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node

    from .source_filters import SourceFilter

logger = logging.getLogger(__name__)


class TypeExtractor:
    """Extracts type requirements from various sources like pipeline nodes."""

    def __init__(self, source_filter: SourceFilter) -> None:
        """Initialize the type extractor.

        Args:
            source_filters: List of source filters to use for extraction.
        """
        self.source_filter = source_filter

    def extract_types_from_pipelines(self) -> dict[str, type]:
        """Extract all type requirements from available pipelines using configured source filters.

        Returns:
            Dictionary mapping source keys to their expected types
        """
        try:
            from kedro.framework.project import pipelines

            pipeline_dict = dict(pipelines)
        except ImportError:
            logger.warning("Could not import pipelines from kedro.framework.project")
            return {}
        except Exception as exc:
            logger.warning("Error importing pipelines: %s", exc)
            return {}

        all_type_requirements: dict[str, type] = {}

        for pipeline_name, pipeline in pipeline_dict.items():
            # Skip __default__ pipeline to avoid duplicate processing
            if pipeline_name == "__default__":
                continue

            pipeline_type_requirements = self._extract_types_from_pipeline(pipeline)

            # Check for conflicting type requirements
            for key, new_type in pipeline_type_requirements.items():
                if key in all_type_requirements:
                    existing_type = all_type_requirements[key]
                    if existing_type != new_type:
                        logger.warning(
                            "Conflicting type requirements for parameter '%s': "
                            "%s (existing) vs %s (from pipeline '%s'). "
                            "Using %s.",
                            key,
                            existing_type.__name__,
                            new_type.__name__,
                            pipeline_name,
                            new_type.__name__,
                        )

            all_type_requirements.update(pipeline_type_requirements)

        logger.debug(
            "Found %d type requirements across all pipelines",
            len(all_type_requirements),
        )
        return all_type_requirements

    def _extract_types_from_pipeline(self, pipeline: Pipeline) -> dict[str, type]:
        """Extract type requirements from a single pipeline.

        Args:
            pipeline: Pipeline object to analyze.

        Returns:
            Dictionary mapping source keys to their expected types.
        """
        type_requirements: dict[str, type] = {}

        for node in getattr(pipeline, "nodes", []):
            node_type_requirements = self._extract_types_from_node(node)
            type_requirements.update(node_type_requirements)

        return type_requirements

    def _extract_types_from_node(self, node: Node) -> dict[str, type]:
        """Extract typed requirements from a single node using the configured source filter.

        Inspects the node's function signature and maps type-annotated parameter
        inputs to their expected types.

        Args:
            node: Node object to analyze.

        Returns:
            Dictionary mapping source keys to their expected types.

        Example:
        ```python
        # Given a node with: def my_func(data: pd.DataFrame, opts: ModelOptions)
        # and inputs=["companies", "params:model_options"]
        # Returns: {"model_options": ModelOptions}
        ```
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

        # Map dataset names to argument names
        dataset_to_arg = self._build_dataset_to_arg_mapping(node, sig)

        # Extract requirements using configured source filter
        all_requirements: dict[str, type] = {}

        for ds_name, arg_name in dataset_to_arg.items():
            expected_type = type_hints.get(arg_name)
            if not expected_type:
                continue

            if self.source_filter.should_process(ds_name):
                source_key = self.source_filter.extract_key(ds_name)
                all_requirements[source_key] = expected_type
                log_message = self.source_filter.get_log_message(
                    source_key, expected_type.__name__
                )
                logger.debug(log_message)

        return all_requirements

    def _build_dataset_to_arg_mapping(
        self, node: Node, signature: inspect.Signature
    ) -> dict[str, str]:
        """Build mapping from dataset names to function argument names.

        Kedro nodes accept inputs as either a list/tuple of dataset names
        (positionally mapped to function arguments) or a dict mapping dataset
        names to argument names. This method normalises both formats.

        Args:
            node: Node object.
            signature: Function signature of the node's function.

        Returns:
            Dictionary mapping dataset names to argument names.

        Example:
        ```python
        # List inputs: ["companies", "params:model_options"]
        # Function: def my_func(data, opts)
        # Returns: {"companies": "data", "params:model_options": "opts"}

        # Dict inputs: {"params:model_options": "opts"}
        # Returns: {"params:model_options": "opts"}
        ```
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

    def resolve_nested_path(self, data: dict, path: str) -> Any:
        """Resolve a dot-separated path to a value in a nested dictionary.

        Args:
            data: Data dictionary.
            path: Dot-separated path (e.g. ``"model.options.test_size"``).

        Returns:
            Value at the specified path, or None if not found.

        Example:
        ```python
        data = {"model": {"options": {"test_size": 0.2}}}
        resolve_nested_path(data, "model.options.test_size")  # 0.2
        resolve_nested_path(data, "model.missing")  # None
        ```
        """
        if "." not in path:
            return data.get(path)

        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def set_nested_value(self, data: dict, path: str, value: Any) -> None:
        """Set a value at a dot-separated path in a nested dictionary.

        Creates intermediate dictionaries as needed.

        Args:
            data: Data dictionary to modify.
            path: Dot-separated path (e.g. ``"model.options.test_size"``).
            value: Value to set.

        Raises:
            ValidationError: If an intermediate key exists but is not a dictionary.

        Example:
        ```python
        data = {}
        set_nested_value(data, "model.options.test_size", 0.3)
        # data == {"model": {"options": {"test_size": 0.3}}}
        ```
        """
        if "." not in path:
            data[path] = value
            return

        keys = path.split(".")
        current = data

        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                # Can't set nested value if intermediate value is not a dict
                raise ValidationError(
                    f"Cannot set nested value '{path}': intermediate key '{key}' is not a dictionary"
                )
            current = current[key]

        # Set the final value
        current[keys[-1]] = value
